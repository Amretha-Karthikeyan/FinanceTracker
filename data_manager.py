"""
Data Manager — Supabase-backed storage for transactions,
investments, and savings.  Falls back to local CSV if
Supabase is not configured.
"""

import os
import pandas as pd
from config import (
    DATA_DIR, TRANSACTIONS_FILE, INVESTMENTS_FILE, SAVINGS_FILE,
    TRANSACTION_COLUMNS, INVESTMENT_COLUMNS, SAVINGS_COLUMNS,
    SUPABASE_URL, SUPABASE_KEY,
)

# ─── Supabase client (lazy singleton) ────────────────────────
_supabase = None


def _get_sb():
    global _supabase
    if _supabase is None and SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def _use_supabase() -> bool:
    return _get_sb() is not None


# ─── Local CSV helpers (fallback) ────────────────────────────

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_csv(path, columns, date_col="date"):
    _ensure_dir()
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=[date_col])
    return pd.DataFrame(columns=columns)


def _save_csv(df, path):
    _ensure_dir()
    df.to_csv(path, index=False)


# ─── Supabase helpers ────────────────────────────────────────

def _sb_load(table: str, columns: list) -> pd.DataFrame:
    """Load all rows from a Supabase table into a DataFrame."""
    sb = _get_sb()
    resp = sb.table(table).select("*").execute()
    if resp.data:
        df = pd.DataFrame(resp.data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    return pd.DataFrame(columns=columns)


def _sb_upsert(table: str, records: list[dict]):
    """Insert rows, ignoring duplicates via on_conflict."""
    sb = _get_sb()
    if not records:
        return
    sb.table(table).upsert(records, on_conflict="id").execute()


def _sb_insert(table: str, records: list[dict]):
    """Insert new rows."""
    sb = _get_sb()
    if not records:
        return
    sb.table(table).insert(records).execute()


def _sb_update_rows(table: str, df: pd.DataFrame):
    """Update existing rows by id."""
    sb = _get_sb()
    for _, row in df.iterrows():
        if "id" in row and pd.notna(row["id"]):
            data = row.to_dict()
            row_id = data.pop("id")
            # Convert date to string for JSON
            for k, v in data.items():
                if isinstance(v, pd.Timestamp):
                    data[k] = v.strftime("%Y-%m-%d")
            sb.table(table).update(data).eq("id", int(row_id)).execute()


def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts with JSON-safe dates."""
    records = df.to_dict(orient="records")
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, pd.Timestamp):
                rec[k] = v.strftime("%Y-%m-%d")
            elif pd.isna(v):
                rec[k] = None
        rec.pop("id", None)  # Let Supabase auto-generate id
    return records


# =====================================================================
# TRANSACTIONS
# =====================================================================

def load_transactions() -> pd.DataFrame:
    if _use_supabase():
        return _sb_load("transactions", TRANSACTION_COLUMNS)
    return _load_csv(TRANSACTIONS_FILE, TRANSACTION_COLUMNS)


def save_transactions(df: pd.DataFrame):
    if _use_supabase():
        _sb_update_rows("transactions", df)
        return
    _save_csv(df, TRANSACTIONS_FILE)


def append_transactions(new_df: pd.DataFrame) -> pd.DataFrame:
    """
    Append new transactions, de-duplicate by (date, description, amount),
    and save. Returns the merged DataFrame.
    """
    existing = load_transactions()
    combined = pd.concat([existing, new_df], ignore_index=True)

    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.drop_duplicates(
        subset=["date", "description", "amount"], keep="first"
    )
    combined = combined.sort_values("date").reset_index(drop=True)

    if "month_year" not in combined.columns or combined["month_year"].isna().any():
        combined["month_year"] = combined["date"].dt.strftime("%Y-%m")

    if _use_supabase():
        # Only insert rows that are truly new (not in existing)
        if not existing.empty:
            merged = combined.merge(
                existing[["date", "description", "amount"]],
                on=["date", "description", "amount"],
                how="left", indicator=True,
            )
            new_only = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
        else:
            new_only = combined
        records = _df_to_records(new_only)
        _sb_insert("transactions", records)
        return load_transactions()
    else:
        _save_csv(combined, TRANSACTIONS_FILE)
        return combined


# =====================================================================
# INVESTMENTS
# =====================================================================

def load_investments() -> pd.DataFrame:
    if _use_supabase():
        return _sb_load("investments", INVESTMENT_COLUMNS)
    return _load_csv(INVESTMENTS_FILE, INVESTMENT_COLUMNS)


def save_investments(df: pd.DataFrame):
    if _use_supabase():
        return
    _save_csv(df, INVESTMENTS_FILE)


def add_investment(record: dict) -> pd.DataFrame:
    """Add a single investment record and save."""
    record = dict(record)
    record["date"] = pd.to_datetime(record["date"])
    record["month_year"] = record["date"].strftime("%Y-%m")
    record["date"] = record["date"].strftime("%Y-%m-%d")

    if _use_supabase():
        _sb_insert("investments", [record])
        return load_investments()

    df = load_investments()
    new_row = pd.DataFrame([record])
    new_row["date"] = pd.to_datetime(new_row["date"])
    df = pd.concat([df, new_row], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)
    _save_csv(df, INVESTMENTS_FILE)
    return df


# =====================================================================
# SAVINGS
# =====================================================================

def load_savings() -> pd.DataFrame:
    if _use_supabase():
        return _sb_load("savings", SAVINGS_COLUMNS)
    return _load_csv(SAVINGS_FILE, SAVINGS_COLUMNS)


def save_savings(df: pd.DataFrame):
    if _use_supabase():
        return
    _save_csv(df, SAVINGS_FILE)


def add_saving(record: dict) -> pd.DataFrame:
    """Add a single savings record and save."""
    record = dict(record)
    record["date"] = pd.to_datetime(record["date"])
    record["month_year"] = record["date"].strftime("%Y-%m")
    record["date"] = record["date"].strftime("%Y-%m-%d")

    if _use_supabase():
        _sb_insert("savings", [record])
        return load_savings()

    df = load_savings()
    new_row = pd.DataFrame([record])
    new_row["date"] = pd.to_datetime(new_row["date"])
    df = pd.concat([df, new_row], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)
    _save_csv(df, SAVINGS_FILE)
    return df


# =====================================================================
# SUMMARY HELPERS
# =====================================================================

def monthly_spending_summary(currency_filter: str = None) -> pd.DataFrame:
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
    df = load_investments()
    if df.empty:
        return df
    if currency_filter:
        df = df[df["currency"] == currency_filter]
    summary = df.groupby(["month_year", "category"])["amount"].sum().reset_index()
    summary = summary.sort_values(["month_year", "amount"], ascending=[True, False])
    return summary


def monthly_savings_summary(currency_filter: str = None) -> pd.DataFrame:
    df = load_savings()
    if df.empty:
        return df
    if currency_filter:
        df = df[df["currency"] == currency_filter]
    summary = df.groupby(["month_year", "category"])["amount"].sum().reset_index()
    summary = summary.sort_values(["month_year", "amount"], ascending=[True, False])
    return summary


def grand_totals() -> dict:
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
