# app/main.py
from __future__ import annotations
import sys, datetime as dt
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui  import QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMenuBar, QFileDialog,
    QComboBox, QMessageBox, QStatusBar, QHeaderView, QAbstractItemView
)

# ---- optional sound
HAVE_SOUND = False
try:
    from PySide6.QtMultimedia import QSoundEffect
    HAVE_SOUND = True
except Exception:
    QSoundEffect = None
    HAVE_SOUND = False

# ---- modules
from .db import (
    init_db, get_settings, set_settings, distinct_years, list_month,
    add_expense, month_total, categories
)
from .add_expense import AddExpenseDialog
from .manage import ManageDialog
from .settings_dialog import SettingsDialog
from .export_pdf import export_month_pdf

APP_DIR   = Path(__file__).parent
ASSETS    = APP_DIR / "assets"
ICON_PATH = ASSETS / "ghost.png"

# ---------------- EMF sound ----------------
class EMFSound:
    def __init__(self, assets_dir: Path, enabled: bool):
        self.enabled = bool(enabled) and HAVE_SOUND
        self.cur_level = 1
        self.effects: dict[int, QSoundEffect] = {}
        if self.enabled:
            for lvl in (2, 3, 4, 5):
                wav = assets_dir / f"emf{lvl}.wav"
                if wav.exists():
                    s = QSoundEffect()
                    s.setSource(QUrl.fromLocalFile(str(wav)))
                    s.setLoopCount(999_999)          # loop “forever”
                    s.setVolume(0.85)
                    self.effects[lvl] = s

    def set_muted(self, muted: bool):
        # apply global mute/unmute
        self.enabled = not muted and HAVE_SOUND
        if muted:
            self.stop()

    def stop(self):
        for s in self.effects.values():
            try: s.stop()
            except Exception: pass
        self.cur_level = 1

    def play_for_level(self, level: int):
        if not self.enabled or not self.effects:
            self.stop()
            return
        level = max(1, min(5, level))
        if level == 1:
            self.stop()
            return
        if level == self.cur_level:
            eff = self.effects.get(level)
            if eff and not eff.isPlaying():
                eff.play()
            return
        # switch level
        self.stop()
        self.cur_level = level
        eff = self.effects.get(level)
        if eff:
            eff.setVolume(0.85)  # make sure a manual stop didn’t zero it
            eff.play()

def emf_level_from_total(total: float) -> int:
    if total >= 2000: return 5
    if total >= 1500: return 4
    if total >= 1000: return 3
    if total >=  500: return 2
    return 1

# ---------------- Main Window ----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phasmo Expense Calculator")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(1120, 720)

        init_db()
        qss = (APP_DIR / "theme.qss")
        if qss.exists():
            self.setStyleSheet(qss.read_text(encoding="utf-8"))

        # settings + sound
        self.settings = get_settings()
        self._sfx = EMFSound(ASSETS, enabled=self.settings["sound_enabled"])
        # <<< important: explicitly sync the sound engine to saved setting
        self._sfx.set_muted(not self.settings["sound_enabled"])

        c = QWidget(); self.setCentralWidget(c)
        root = QVBoxLayout(c)

        title = QLabel("<b>Phasmo Expense Calculator</b>")
        title.setAlignment(Qt.AlignCenter)
        self.lbl_total = QLabel("Monthly Total: £0.00")
        self.emf_dot = QLabel(); self.emf_dot.setFixedSize(14, 14)
        self.emf_dot.setStyleSheet("background:#6eb6ff;border-radius:7px;border:1px solid #2a2a2a;")
        self.lbl_emf = QLabel("EMF 1")

        hdr = QHBoxLayout()
        hdr.addWidget(title); hdr.addStretch(1)
        hdr.addWidget(self.lbl_total); hdr.addSpacing(8)
        hdr.addWidget(self.emf_dot);   hdr.addSpacing(4)
        hdr.addWidget(self.lbl_emf);   hdr.addStretch(1)
        root.addLayout(hdr)

        self.cmb_year, self.cmb_month = QComboBox(), QComboBox()
        self._fill_years(); self._fill_months()
        self.cmb_year.currentIndexChanged.connect(self.reload)
        self.cmb_month.currentIndexChanged.connect(self.reload)

        btn_add = QPushButton("Add Expense")
        btn_mng = QPushButton("Manage Expenses")
        btn_pdf = QPushButton("Export PDF")
        btn_add.clicked.connect(self.on_add)
        btn_mng.clicked.connect(self.on_manage)
        btn_pdf.clicked.connect(self.on_export)

        row = QHBoxLayout()
        row.addWidget(self.cmb_year); row.addWidget(self.cmb_month)
        row.addSpacing(12)
        row.addWidget(btn_add); row.addWidget(btn_mng); row.addWidget(btn_pdf)
        row.addStretch(1)
        root.addLayout(row)

        # table (Description centered)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date","Category","Description","Amount"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Description
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        root.addWidget(self.table, 1)

        mb = QMenuBar(self)
        m_file = mb.addMenu("File")
        m_file.addAction("Export PDF…", self.on_export)
        m_file.addSeparator()
        m_file.addAction("Exit", self.close)
        m_tools = mb.addMenu("Tools")
        m_tools.addAction("Settings…", self.on_settings)
        m_help = mb.addMenu("Help")
        m_help.addAction("About…", lambda: QMessageBox.information(
            self, "About", "Only god can help you, Enjoy !\nThis app is made by Denikks"
        ))
        self.setMenuBar(mb); self.setStatusBar(QStatusBar(self))

        self._select_now(); self.reload()

    # helpers
    def _fill_years(self):
        ys = distinct_years(); cy = dt.date.today().year
        if cy not in ys: ys.append(cy)
        for y in sorted(set(ys)): self.cmb_year.addItem(str(y))
    def _fill_months(self):
        import calendar
        for m in range(1,13): self.cmb_month.addItem(calendar.month_name[m])
    def _select_now(self):
        t = dt.date.today()
        self.cmb_year.setCurrentText(str(t.year))
        self.cmb_month.setCurrentIndex(t.month-1)
    def _current_y_m(self): return int(self.cmb_year.currentText()), self.cmb_month.currentIndex()+1
    def _set_emf_ui(self, level):
        colors={1:"#6eb6ff",2:"#36b24a",3:"#ffd84a",4:"#ff8f2b",5:"#ff3737"}
        self.emf_dot.setStyleSheet(f"background:{colors[level]};border-radius:7px;border:1px solid #2a2a2a;")
        self.lbl_emf.setText(f"EMF {level}")

    # refresh
    def reload(self):
        y,m = self._current_y_m()
        rows = list_month(y,m)
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount(); self.table.insertRow(i)
            self.table.setItem(i,0,QTableWidgetItem(r["date"]))
            self.table.setItem(i,1,QTableWidgetItem(r["category"]))
            desc = QTableWidgetItem(r["description"] or "")
            desc.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)   # centered
            self.table.setItem(i,2,desc)
            amt = QTableWidgetItem(f"{r['amount']:.2f}")
            amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i,3,amt)
            self.table.setRowHeight(i,22)

        cur = get_settings()["currency"]; total = month_total(y,m)
        self.lbl_total.setText(f"Monthly Total: {cur}{total:.2f}")

        lvl = emf_level_from_total(total)
        self._set_emf_ui(lvl)
        self._sfx.play_for_level(lvl)   # keep audio in sync on every reload

    # actions
    def on_add(self):
        dlg = AddExpenseDialog(self)
        if dlg.exec():
            v = dlg.values()
            add_expense(v["date"], v["category"], v["description"], v["amount"])
            self.reload()
    def on_manage(self):
        y,m = self._current_y_m()
        dlg = ManageDialog(y,m,self); dlg.exec(); self.reload()
    def on_settings(self):
        ok, enabled, cur = SettingsDialog.edit(self)
        if ok:
            self._sfx.set_muted(not enabled)  # apply immediately
            self.reload()
    def on_export(self):
        y,m = self._current_y_m(); cur = get_settings()["currency"]
        path,_ = QFileDialog.getSaveFileName(self,"Save monthly PDF",f"expenses_{y}-{m:02d}.pdf","PDF (*.pdf)")
        if not path: return
        try:
            export_month_pdf(path,y,m,cur)
            QMessageBox.information(self,"Export","PDF saved.")
        except Exception as e:
            QMessageBox.critical(self,"Export failed",f"{e}")

def main():
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
