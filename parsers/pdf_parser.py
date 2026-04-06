"""
PDF Statement Parser
Supports Citibank SG and OCBC SG credit-card statement layouts.
Uses pdfplumber for text extraction and regex-based line parsing.
"""

import re
import pdfplumber
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple


# ─── Lines to skip (noise) ───────────────────────────────────
SKIP_PATTERNS = [
    r"BALANCE\s*PREVIOUS",
    r"LAST\s*MONTH",
    r"SUB-?\s*TOTAL",
    r"GRAND\s*TOTAL",
    r"TOTAL\s*AMOUNT",
    r"^SUBTOTAL",
    r"^TOTAL\b",
    r"FOREIGN\s*CURRENCY",
    r"PREVIOUS\s+PAYMENTS",
    r"STATEMENT\s*DATE",
    r"PAYMENT\s*DUE",
    r"PAGE\s+\d+\s+OF",
    r"CREDIT\s*LIMIT",
    r"XXXX-XXXX",
    r"MINIMUM\s*PAYMENT",
    r"INTEREST\s*RATE",
    r"TRANSACTION(S)?\s*FOR\b",
    r"ALL\s*TRANSACTIONS?\s*BILLED",
    r"KINDLY\s*ENSURE",
    r"REWARD|REBATE|SMRT\$|CASHBACK\s+(carried|earned)",
    r"^RetailInterestRate",
    r"^CashInterestRate",
    r"\bCREDIT\s*CARD\s*TYPE\b",
    r"\bACCOUNT\s*NUMBER\b",
    r"YOURCITIBANKCARDS",
    r"PAYMENTSLIP",
    r"CITISMRTPLATINUM\b",
    r"CITICASHBACK\b.*CARD\b",
]
_SKIP_RE = re.compile("|".join(SKIP_PATTERNS), re.IGNORECASE)

# ─── Date patterns (order matters — most specific first) ─────
# Each entry: (compiled_regex, strptime_format, needs_year_fallback)
_DATE_DEFS: List[Tuple[re.Pattern, str, bool]] = [
    # DD/MM/YYYY or DD-MM-YYYY
    (re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b"), None, False),
    # DD MMM YYYY  (05 Jan 2026)
    (re.compile(r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b", re.I), None, False),
    # YYYY-MM-DD
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"), "%Y-%m-%d", False),
    # DDMMM  (16FEB, 01MAR — Citibank, no space, no year)
    (re.compile(r"(?:^|\s)(\d{2}(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))\b", re.I), "%d%b", True),
    # DD MMM  (5 Jan — with space, no year)
    (re.compile(r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\b", re.I), "%d %b", True),
    # DD/MM  (04/03 — OCBC, no year)
    (re.compile(r"^(\d{2}/\d{2})\b"), "%d/%m", True),
    # DD/MM/YY
    (re.compile(r"\b(\d{2}/\d{2}/\d{2})\b"), "%d/%m/%y", False),
]

# Amount with optional CR/DR suffix
_AMT_RE = re.compile(r"([\d,]+\.\d{2})\s*(CR|DR)?", re.I)
# Parenthesized credit amount  e.g. (1,847.30)
_CREDIT_AMT_RE = re.compile(r"\(([\d,]+\.\d{2})\)")


# ═════════════════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════════════════

def parse_pdf_statement(
    pdf_path: str,
    currency: str = "SGD",
    statement_year: int = None,
) -> pd.DataFrame:
    if statement_year is None:
        statement_year = datetime.now().year

    all_txns: List[Dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                txn = _parse_line(line, currency, statement_year)
                if txn:
                    all_txns.append(txn)

    if not all_txns:
        all_txns = _parse_via_tables(pdf_path, currency, statement_year)

    df = pd.DataFrame(all_txns)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df


def extract_statement_period(pdf_path: str) -> Optional[str]:
    with pdfplumber.open(pdf_path) as pdf:
        if pdf.pages:
            text = pdf.pages[0].extract_text() or ""
            m = re.search(
                r"(?:statement\s+(?:period|date)|billing\s+period|period)"
                r"[:\s]+(\d{1,2}\s+\w+\s+\d{4})\s*[-–to]+\s*(\d{1,2}\s+\w+\s+\d{4})",
                text, re.I,
            )
            if m:
                end_date = _parse_date_str(m.group(2))
                if end_date:
                    return end_date.strftime("%b %Y")
            m2 = re.search(
                r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
                text, re.I,
            )
            if m2:
                return m2.group(1)
    return None


# ═════════════════════════════════════════════════════════════
# Internal helpers
# ═════════════════════════════════════════════════════════════

def _parse_date_str(text: str, fallback_year: int = None) -> Optional[datetime]:
    text = text.strip()
    year = fallback_year or datetime.now().year
    # For formats without a year, inject the fallback year before parsing
    # to avoid Python 3.15+ deprecation warnings
    fmts_with_year = [
        ("%d/%m/%Y", False), ("%d-%m-%Y", False), ("%d %b %Y", False),
        ("%d %B %Y", False), ("%Y-%m-%d", False), ("%d/%m/%y", False),
    ]
    fmts_no_year = [
        ("%d/%m", "%d/%m/%Y"), ("%d %b", "%d %b %Y"), ("%d%b", "%d%b%Y"),
    ]
    for fmt, _ in fmts_with_year:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    # For formats without year, append year to string and format
    for short_fmt, full_fmt in fmts_no_year:
        try:
            datetime.strptime(text, short_fmt)  # validate pattern
            return datetime.strptime(f"{text}{year}", f"{short_fmt}%Y")
        except ValueError:
            continue
    return None


def _find_date(line: str) -> Optional[Tuple[re.Match, str, bool]]:
    """Return (match_obj, date_string, needs_year_fallback) or None."""
    for regex, _, needs_year in _DATE_DEFS:
        m = regex.search(line)
        if m:
            return m, m.group(1), needs_year
    return None


def _clean_amount(text: str) -> float:
    return float(text.replace(",", ""))


def _is_noise(line: str) -> bool:
    return bool(_SKIP_RE.search(line))


def _parse_line(line: str, currency: str, year: int) -> Optional[Dict]:
    """Parse a single text line into a transaction dict."""
    line = line.strip()
    if not line or _is_noise(line):
        return None

    found = _find_date(line)
    if not found:
        return None
    date_match, date_str, needs_year = found
    parsed_date = _parse_date_str(date_str, fallback_year=year if needs_year else None)
    if not parsed_date:
        return None

    after_date = line[date_match.end():].strip()

    # ── Check for parenthesized credit amount, e.g. (1,847.30) ──
    credit_m = _CREDIT_AMT_RE.search(after_date)
    if credit_m:
        amount = _clean_amount(credit_m.group(1))
        desc = after_date[:credit_m.start()].strip()
        desc = _clean_desc(desc)
        if not desc:
            return None
        return _txn(parsed_date, desc, amount, "credit", currency)

    # ── Regular amount(s) ────────────────────────────────────
    amounts = list(_AMT_RE.finditer(after_date))
    if not amounts:
        return None

    # Use the LAST amount on the line (transaction amount)
    amt_match = amounts[-1]
    amount = _clean_amount(amt_match.group(1))
    dr_cr = amt_match.group(2)
    txn_type = "credit" if (dr_cr and dr_cr.upper() == "CR") else "debit"

    desc = after_date[:amt_match.start()].strip()
    # Remove any intermediate amounts (balance columns etc.)
    if len(amounts) > 1:
        desc = after_date[:amounts[0].start()].strip()
        # If first amount IS the transaction amount (only one meaningful),
        # keep the wider description
        if not desc:
            desc = after_date[:amt_match.start()].strip()

    desc = _clean_desc(desc)
    if not desc:
        return None

    # Extra guard: skip if description looks like a summary/header line
    if re.match(r"^\d[\d,]*\.\d{2}$", desc):
        return None

    return _txn(parsed_date, desc, amount, txn_type, currency)


def _clean_desc(desc: str) -> str:
    """Normalise whitespace, strip stray amounts and trailing country codes."""
    desc = re.sub(r"\s+", " ", desc).strip()
    # Remove stray embedded amounts like "SGD 66.31"
    desc = re.sub(r"\b[A-Z]{3}\s+[\d,]+\.\d{2}\b", "", desc).strip()
    # Remove trailing 2-letter country codes that pdfplumber sometimes leaves
    desc = re.sub(r"\s+[A-Z]{2}$", "", desc).strip()
    # Remove leading dash + 4-digit card suffix (OCBC style: -6061 ...)
    desc = re.sub(r"^-\d{4}\s+", "", desc).strip()
    return desc


def _txn(dt, desc, amount, txn_type, currency):
    return {
        "date": dt,
        "description": desc,
        "amount": amount,
        "type": txn_type,
        "currency": currency,
    }


def _parse_via_tables(
    pdf_path: str, currency: str, year: int
) -> List[Dict]:
    """Fallback: use pdfplumber's table extraction."""
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    for i, cell in enumerate(row):
                        if cell is None:
                            continue
                        found = _find_date(str(cell))
                        if found:
                            _, ds, ny = found
                            parsed_date = _parse_date_str(ds, year if ny else None)
                            if not parsed_date:
                                continue
                            desc_parts = []
                            amount = None
                            txn_type = "debit"
                            for j, col in enumerate(row):
                                if j == i or col is None:
                                    continue
                                col_str = str(col).strip()
                                cm = _CREDIT_AMT_RE.search(col_str)
                                am = _AMT_RE.search(col_str)
                                if cm:
                                    amount = _clean_amount(cm.group(1))
                                    txn_type = "credit"
                                elif am:
                                    amount = _clean_amount(am.group(1))
                                    if am.group(2) and am.group(2).upper() == "CR":
                                        txn_type = "credit"
                                elif col_str and not re.match(r"^[\d,.\s]+$", col_str):
                                    desc_parts.append(col_str)
                            if amount and desc_parts:
                                transactions.append(
                                    _txn(parsed_date, " ".join(desc_parts), amount, txn_type, currency)
                                )
                            break
    return transactions
