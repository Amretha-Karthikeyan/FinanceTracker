"""
PDF Statement Parser
Supports common bank / credit-card statement layouts.
Uses pdfplumber for text extraction and regex-based line parsing.
"""

import re
import pdfplumber
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional


# ─── Common date patterns found in statements ────────────────
DATE_PATTERNS = [
    # DD/MM/YYYY, DD-MM-YYYY
    r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b",
    # DD MMM YYYY  (e.g. 05 Jan 2026)
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
    # DD MMM  (e.g. 05 Jan — year inferred)
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\b",
    # DDMMM  (e.g. 16FEB, 01MAR — no space, Citibank style)
    r"(?:^|\s)(\d{2}(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))\b",
    # YYYY-MM-DD
    r"\b(\d{4}-\d{2}-\d{2})\b",
    # DD/MM/YY
    r"\b(\d{2}/\d{2}/\d{2})\b",
]

# Amount patterns — handles 1,234.56 or 1234.56 with optional CR/DR suffix
AMOUNT_PATTERN = r"[\$S]*\s*([\d,]+\.\d{2})\s*(CR|DR|cr|dr)?"
# Parenthesized amounts indicate credits, e.g. (1,847.30)
CREDIT_AMOUNT_PATTERN = r"\(([\d,]+\.\d{2})\)"


def _parse_date(text: str, fallback_year: int = None) -> Optional[datetime]:
    """Try multiple date formats and return a datetime or None."""
    text = text.strip()
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y",
        "%Y-%m-%d", "%d/%m/%y", "%d %b", "%d%b",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            # If year was not in the pattern, set fallback
            if fmt in ("%d %b", "%d%b") and fallback_year:
                dt = dt.replace(year=fallback_year)
            elif fmt in ("%d %b", "%d%b"):
                dt = dt.replace(year=datetime.now().year)
            return dt
        except ValueError:
            continue
    return None


def _clean_amount(text: str) -> float:
    """Convert '1,234.56' → 1234.56"""
    return float(text.replace(",", ""))


def parse_pdf_statement(
    pdf_path: str,
    currency: str = "SGD",
    statement_year: int = None,
) -> pd.DataFrame:
    """
    Parse a bank / credit-card PDF statement and return a DataFrame of
    transactions with columns: date, description, amount, type, currency.
    
    The parser uses a two-pass strategy:
      1. Extract all text lines from each page.
      2. For each line, look for a date + amount pattern to identify
         transaction rows.  Everything between date and amount is the
         description.
    """
    if statement_year is None:
        statement_year = datetime.now().year

    all_transactions: List[Dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            for line in lines:
                txn = _parse_transaction_line(line, currency, statement_year)
                if txn:
                    all_transactions.append(txn)

    if not all_transactions:
        # Fallback: try table extraction
        all_transactions = _parse_via_tables(pdf_path, currency, statement_year)

    df = pd.DataFrame(all_transactions)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    return df


def _parse_transaction_line(
    line: str, currency: str, year: int
) -> Optional[Dict]:
    """Attempt to parse a single text line into a transaction dict."""
    # Try each date pattern
    date_match = None
    date_str = None
    for pat in DATE_PATTERNS:
        m = re.search(pat, line, re.IGNORECASE)
        if m:
            date_match = m
            date_str = m.group(1)
            break

    if not date_match:
        return None

    parsed_date = _parse_date(date_str, fallback_year=year)
    if not parsed_date:
        return None

    # Check for parenthesized (credit) amount first, e.g. (1,847.30)
    credit_match = re.search(CREDIT_AMOUNT_PATTERN, line)
    if credit_match:
        amount = _clean_amount(credit_match.group(1))
        desc_start = date_match.end()
        desc_end = credit_match.start()
        description = line[desc_start:desc_end].strip()
        description = re.sub(r"\s+", " ", description)
        if not description:
            description = line[date_match.end():].strip()
            description = re.sub(CREDIT_AMOUNT_PATTERN, "", description).strip()
            description = re.sub(AMOUNT_PATTERN, "", description).strip()
        if not description:
            return None
        return {
            "date": parsed_date,
            "description": description,
            "amount": amount,
            "type": "credit",
            "currency": currency,
        }

    # Find amount(s) in the line
    amounts = list(re.finditer(AMOUNT_PATTERN, line))
    if not amounts:
        return None

    # Use the LAST amount on the line (usually the transaction amount)
    amt_match = amounts[-1]
    amount = _clean_amount(amt_match.group(1))
    dr_cr = amt_match.group(2)

    # Determine debit vs credit
    txn_type = "debit"
    if dr_cr and dr_cr.upper() == "CR":
        txn_type = "credit"

    # Description = text between date and amount
    desc_start = date_match.end()
    desc_end = amt_match.start()
    description = line[desc_start:desc_end].strip()

    # Clean up description
    description = re.sub(r"\s+", " ", description)
    # Remove stray amounts in middle (sometimes balance column)
    # Keep only meaningful text
    if len(description) < 2:
        description = line[date_match.end():].strip()
        description = re.sub(AMOUNT_PATTERN, "", description).strip()

    if not description:
        return None

    return {
        "date": parsed_date,
        "description": description,
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
                    # Try to find date in first columns
                    for i, cell in enumerate(row):
                        if cell is None:
                            continue
                        parsed_date = None
                        for pat in DATE_PATTERNS:
                            m = re.search(pat, str(cell), re.IGNORECASE)
                            if m:
                                parsed_date = _parse_date(m.group(1), year)
                                break
                        if parsed_date:
                            # Find amount in remaining columns
                            desc_parts = []
                            amount = None
                            txn_type = "debit"
                            for j, col in enumerate(row):
                                if j == i or col is None:
                                    continue
                                col_str = str(col).strip()
                                am = re.search(AMOUNT_PATTERN, col_str)
                                if am:
                                    try:
                                        amount = _clean_amount(am.group(1))
                                        if am.group(2) and am.group(2).upper() == "CR":
                                            txn_type = "credit"
                                    except:
                                        pass
                                else:
                                    if col_str and not re.match(r"^[\d,.\s]+$", col_str):
                                        desc_parts.append(col_str)

                            if amount and desc_parts:
                                transactions.append({
                                    "date": parsed_date,
                                    "description": " ".join(desc_parts),
                                    "amount": amount,
                                    "type": txn_type,
                                    "currency": currency,
                                })
                            break  # found date in this row, move on
    return transactions


def extract_statement_period(pdf_path: str) -> Optional[str]:
    """Try to extract statement period (month/year) from the first page."""
    with pdfplumber.open(pdf_path) as pdf:
        if pdf.pages:
            text = pdf.pages[0].extract_text() or ""
            # Look for patterns like "Statement Period: 01 Jan 2026 - 31 Jan 2026"
            m = re.search(
                r"(?:statement\s+(?:period|date)|billing\s+period|period)"
                r"[:\s]+(\d{1,2}\s+\w+\s+\d{4})\s*[-–to]+\s*(\d{1,2}\s+\w+\s+\d{4})",
                text, re.IGNORECASE
            )
            if m:
                end_date = _parse_date(m.group(2))
                if end_date:
                    return end_date.strftime("%b %Y")
            # Look for month/year in header
            m2 = re.search(
                r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
                text, re.IGNORECASE
            )
            if m2:
                return m2.group(1)
    return None
