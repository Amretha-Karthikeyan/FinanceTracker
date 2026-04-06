"""
Finance Tracker Configuration
Currencies: SGD & INR
Categories for Spending, Investments, and Savings
"""

# ─── Currencies ───────────────────────────────────────────────
CURRENCIES = ["SGD", "INR"]
DEFAULT_CURRENCY = "SGD"

# ─── Spending Categories & Auto-Classification Keywords ───────
SPENDING_CATEGORIES = {
    "Groceries": [
        "fairprice", "ntuc", "cold storage", "sheng siong", "giant",
        "redmart", "grocery", "supermarket", "provision", "market",
        "dmart", "big bazaar", "reliance fresh", "more supermarket",
        "bigbasket", "zepto", "blinkit", "swiggy instamart",
    ],
    "Rent / EMI": [
        "rent", "emi", "home loan", "mortgage", "housing",
        "hdb", "property tax", "condo",
    ],
    "Utilities": [
        "sp group", "sp services", "singtel", "starhub", "m1",
        "electricity", "water", "gas", "internet", "broadband",
        "telco", "mobile", "airtel", "jio", "bsnl", "vodafone",
        "bescom", "bwssb",
    ],
    "Transport": [
        "grab", "gojek", "comfort", "citycab", "taxi", "uber",
        "mrt", "bus", "ez-link", "transit", "petrol", "fuel",
        "parking", "shell", "esso", "caltex", "ola", "rapido",
        "metro", "toll",
    ],
    "Dining": [
        "restaurant", "cafe", "coffee", "starbucks", "mcdonald",
        "kfc", "pizza", "foodpanda", "deliveroo", "grabfood",
        "swiggy", "zomato", "food", "dining", "eat", "hawker",
        "kopitiam", "toast box",
    ],
    "Shopping": [
        "amazon", "lazada", "shopee", "courts", "ikea", "uniqlo",
        "h&m", "zara", "flipkart", "myntra", "ajio",
        "decathlon", "don quijote", "mustafa", "takashimaya",
        "tangs", "robinsons", "mall",
    ],
    "Health": [
        "hospital", "clinic", "pharmacy", "doctor", "medical",
        "dental", "guardian", "watsons", "apollo", "medlife",
        "practo", "gym", "fitness",
    ],
    "Education": [
        "school", "tuition", "course", "udemy", "coursera",
        "university", "college", "books", "education", "training",
        "skillsfuture",
    ],
    "Entertainment": [
        "netflix", "spotify", "disney", "cinema", "movie",
        "theatre", "concert", "ticket", "game", "steam",
        "playstation", "xbox", "hotstar", "prime video",
    ],
    "Subscriptions": [
        "subscription", "membership", "annual", "monthly plan",
        "premium", "apple", "google one", "icloud", "youtube premium",
        "chatgpt", "notion",
    ],
    "Insurance": [
        "insurance", "prudential", "aia", "great eastern", "ntuc income",
        "lic", "hdfc life", "icici pru", "policy",
    ],
    "Personal Care": [
        "salon", "barber", "spa", "beauty", "cosmetic",
        "skincare", "parlour",
    ],
    "Miscellaneous": [],  # Catch-all
}

# ─── Investment Categories ────────────────────────────────────
INVESTMENT_CATEGORIES = [
    "Mutual Funds",
    "Stocks / ETF",
    "Fixed Deposit (FD)",
    "PPF",
    "NPS",
    "Gold",
    "Crypto",
    "Bonds",
    "REIT",
    "CPF Top-Up",
    "SRS",
    "Other Investment",
]

# ─── Savings Categories ──────────────────────────────────────
SAVINGS_CATEGORIES = [
    "Emergency Fund",
    "Savings Account",
    "Recurring Deposit (RD)",
    "Goal-Based Saving",
    "Other Saving",
]

# ─── Data file paths ─────────────────────────────────────────
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.csv")
INVESTMENTS_FILE = os.path.join(DATA_DIR, "investments.csv")
SAVINGS_FILE = os.path.join(DATA_DIR, "savings.csv")

# ─── Supabase ─────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # anon/public key

# CSV column definitions
TRANSACTION_COLUMNS = [
    "date", "description", "amount", "currency", "category",
    "source_file", "month_year", "type",  # debit / credit
]

INVESTMENT_COLUMNS = [
    "date", "category", "description", "amount", "currency",
    "platform", "month_year",
]

SAVINGS_COLUMNS = [
    "date", "category", "description", "amount", "currency",
    "month_year",
]
