"""
Data Manager — persistent CSV-based storage for transactions,
investments, and savings.
"""

import os
import pandas as pd
from config import (
    DATA_DIR, TRANSACTIONS_FILE, INVESTMENTS_FILE, SAVINGS_FILE,
    TRANSACTION_COLUMNS, INVESTMENT_COLUMNS, SAVINGS_COLUMNS,
)


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


# ─── Transactions ─────────────────────────────────────────────

def load_transactions() -> pd.DataFrame:
    _ensure_dir()
    if os.path.exists(TRANSACTIONS_FILE):
        df = pd.read_csv(TRANSACTIONS_FILE, parse_dates=["date"])
        return df
    return pd.DataFrame(columns=TRANSACTION_COLUMNS)


def save_transactions(df: pd.DataFrame):
    _ensure_dir()
    df.to_csv(TRANSACTIONS_FILE, index=False)


def append_transactions(new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Append new transactions, de-duplicate by (date, description, amount),
    and save. Returns the merged DataFrame.
    """
    existing = load_transactions()
    combined = pd.concat([existing, new_df], ignore_index=True)

    # De-duplicate
    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.drop_duplicates(
        subset=["date", "description", "amount"], keep="first"
    )
    combined = combined.sort_values("date").reset_index(drop=True)

    # Ensure month_year column
    if "month_year" not in combined.columns or combined["month_year"].isna().any():
        combined["month_year"] = combined["date"].dt.strftime("%Y-%m")

    save_transactions(combined)
    return combined


# ─── Investments ──────────────────────────────────────────────

def load_investments() -> pd.DataFrame:
    _ensure_dir()
    if os.path.exists(INVESTMENTS_FILE):
        df = pd.read_csv(INVESTMENTS_FILE, parse_dates=["date"])
        return df
    return pd.DataFrame(columns=INVESTMENT_COLUMNS)


def save_investments(df: pd.DataFrame):
    _ensure_dir()
    df.to_csv(INVESTMENTS_FILE, index=False)


def add_investment(record: dict) -> pd.DataFrame:
    """Add a single investment record and save."""
    df = load_investments()
    new_row = pd.DataFrame([record])
    new_row["date"] = pd.to_datetime(new_row["date"])
    new_row["month_year"] = new_row["date"].dt.strftime("%Y-%m")
    df = pd.concat([df, new_row], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)
    save_investments(df)
    return df


# ─── Savings ──────────────────────────────────────────────────

def load_savings() -> pd.DataFrame:
    _ensure_dir()
    if os.path.exists(SAVINGS_FILE):
        df = pd.read_csv(SAVINGS_FILE, parse_dates=["date"])
        return df
    return pd.DataFrame(columns=SAVINGS_COLUMNS)


def save_savings(df: pd.DataFrame):
    _ensure_dir()
    df.to_csv(SAVINGS_FILE, index=False)


def add_saving(record: dict) -> pd.DataFrame:
    """Add a single savings record and save."""
    df = load_savings()
    new_row = pd.DataFrame([record])
    new_row["date"] = pd.to_datetime(new_row["date"])
    new_row["month_year"] = new_row["date"].dt.strftime("%Y-%m")
    df = pd.concat([df, new_row], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)
    save_savings(df)
    return df


# ─── Summary Helpers ──────────────────────────────────────────

def monthly_spending_summary(currency_filter: str = None) -> pd.DataFrame:
    """Category-wise spending by month."""
    df = load_transactions()
    if df.empty:
        return df
    if currency_filter:
        df = df[df["currency"] == currency_filter]
    df = df[df["type"] == "debit"]
    summary = df.groupby(["month_year", "category"])["amount"].sum().reset_index()
    summary = summary.sort_values(["month_year", "amount"], ascending=[True, False])
    return summary


def monthly_investment_summary(currency_filter: str = None) -> pd.DataFrame:
    """Category-wise investments by month."""
    df = load_investments()
    if df.empty:
        return df
    if currency_filter:
        df = df[df["currency"] == currency_filter]
    summary = df.groupby(["month_year", "category"])["amount"].sum().reset_index()
    summary = summary.sort_values(["month_year", "amount"], ascending=[True, False])
    return summary


def monthly_savings_summary(currency_filter: str = None) -> pd.DataFrame:
    """Category-wise savings by month."""
    df = load_savings()
    if df.empty:
        return df
    if currency_filter:
        df = df[df["currency"] == currency_filter]
    summary = df.groupby(["month_year", "category"])["amount"].sum().reset_index()
    summary = summary.sort_values(["month_year", "amount"], ascending=[True, False])
    return summary


def grand_totals() -> dict:
    """Return total spending, investments, savings across all time."""
    txn = load_transactions()
    inv = load_investments()
    sav = load_savings()

    spend = txn[txn["type"] == "debit"]["amount"].sum() if not txn.empty else 0
    credit = txn[txn["type"] == "credit"]["amount"].sum() if not txn.empty else 0
    invest = inv["amount"].sum() if not inv.empty else 0
    save = sav["amount"].sum() if not sav.empty else 0

    return {
        "total_spending": spend,
        "total_credits": credit,
        "total_investments": invest,
        "total_savings": save,
    }
