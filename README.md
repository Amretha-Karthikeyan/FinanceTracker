# 💰 Household Finance Tracker

A Streamlit-based personal finance dashboard that parses bank/card PDF statements and tracks your **spending**, **investments**, and **savings** — month by month, category by category.

**Currencies supported:** SGD 🇸🇬 & INR 🇮🇳

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **PDF Statement Upload** | Upload credit/debit card PDF statements; transactions are auto-extracted |
| **Auto-Categorization** | Each transaction is auto-classified into categories (Groceries, Dining, Transport, etc.) using keyword matching |
| **Editable Categories** | Review and change categories before saving; re-categorize anytime |
| **Monthly Dashboard** | Pie charts, bar charts, and summary tables for spending by category |
| **Investment Tracker** | Manually add investments (Mutual Funds, Stocks, FD, PPF, NPS, Gold, Crypto…) with category-level summaries |
| **Savings Tracker** | Track Emergency Fund, Savings Account, RD contributions |
| **Monthly Trends** | Line chart showing Spending vs Investment vs Savings over time |
| **Multi-Currency** | Toggle between SGD and INR |
| **CSV Export** | Download filtered data as CSV anytime |
| **Persistent Storage** | All data saved in CSV files under `data/` — survives restarts |

---

## 🚀 Quick Start

### 1. Install Python dependencies

```bash
cd FinanceTracker
pip install -r requirements.txt
```

### 2. Run the app

```bash
streamlit run app.py
```

The dashboard opens at **http://localhost:8501**.

---

## 📁 Project Structure

```
FinanceTracker/
├── app.py                # Streamlit dashboard (main entry point)
├── config.py             # Categories, keywords, settings
├── categorizer.py        # Auto-categorization engine
├── data_manager.py       # CSV-based data persistence
├── parsers/
│   ├── __init__.py
│   └── pdf_parser.py     # PDF statement parser (pdfplumber)
├── data/                 # Auto-created — stores your data
│   ├── transactions.csv
│   ├── investments.csv
│   └── savings.csv
├── requirements.txt
└── README.md
```

---

## 📄 How to Upload Statements

1. Go to **📄 Upload Statement** in the sidebar
2. Select currency (SGD/INR) and statement year
3. Upload one or more PDF files
4. Review the parsed transactions — edit categories if needed
5. Click **💾 Save** to persist

### Supported PDF Formats
The parser works with most bank/card statements that have:
- Date + Description + Amount per line
- Tabular layouts with date, description, and amount columns

If your PDF doesn't parse well, you can also manually add transactions in the **💳 Transactions** page.

---

## 📈 Adding Investments & Savings

Go to the **📈 Investments** or **🏦 Savings** page and use the form to manually add entries. Each entry is tagged with a category, date, and amount — giving you full month-by-month category breakdowns.

---

## ⚙️ Customizing Categories

Edit `config.py` to:
- Add/remove **spending categories** and their matching keywords
- Add/remove **investment categories** (Mutual Funds, Stocks, etc.)
- Add/remove **savings categories** (Emergency Fund, RD, etc.)

The auto-categorizer uses **keyword matching** — if a keyword appears in a transaction description, it maps to that category.

---

## 📊 Dashboard Views

- **Spending Breakdown**: Pie + bar charts by category, with summary table
- **Investment Breakdown**: Allocation pie chart and category table
- **Savings Breakdown**: Same as above for savings
- **Monthly Trends**: Line chart comparing spending, investment, and savings month over month

---

## 💡 Tips

- Upload statements monthly to keep your data current
- Use the **month filter** on the dashboard to compare months
- Re-categorize transactions on the **💳 Transactions** page if the auto-categorizer misses
- Add keywords to `config.py` for recurring merchants you see often

---

**Built with** Streamlit • Pandas • Plotly • pdfplumber
