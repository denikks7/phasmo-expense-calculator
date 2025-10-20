# 🧮 Phasmo Expense Calculator

**Phasmo Expense Calculator** is a lightweight desktop app built in **Python** (packaged with PyInstaller) that helps *Phasmophobia* players quickly calculate and track in-game or custom expenses. It provides an easy-to-use interface for managing costs, comparing runs, and tracking item losses — no need for spreadsheets or manual math.

---

## 🚀 Features

- **Simple, intuitive interface** — just run the `.exe`, no installation required  
- **Automatic data handling** — saves user inputs in a dedicated `data` folder  
- **Fast & offline** — works completely locally once built  
- **Cross-platform ready** — developed in Python (tested on Windows)  
- **Easily shareable build** — can be zipped and shared as a standalone app  

---

## 🛠️ Built With

- **Python 3.x**  
- **PyInstaller** — for packaging into an executable  
- **tkinter** — for the GUI (if applicable)  
- **pandas / openpyxl (optional)** — for data management (if used)

---

## 📁 Project Structure

phasmo-expense-calculator/
│
├── app/
│ └── data/ # User data storage (auto-created)
├── dist/
│ └── PhasmoExpenseCalculator/
│ └── PhasmoExpenseCalculator.exe
├── src/ # Source Python scripts (optional)
├── main.py
├── README.md
└── requirements.txt


---

## ⚙️ How to Run

1. Download or clone this repository  
2. Extract and open the project folder  
3. Run the executable:
   ```bash
   dist/PhasmoExpenseCalculator/PhasmoExpenseCalculator.exe
