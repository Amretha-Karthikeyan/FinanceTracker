"""
Auto-categorizer for transactions.
Uses keyword matching against config.SPENDING_CATEGORIES.
Falls back to 'Miscellaneous' if no match found.
"""

from config import SPENDING_CATEGORIES


def categorize_transaction(description: str) -> str:
    """
    Match a transaction description to a spending category using
    keyword lookup. Returns the best matching category name.
    """
    desc_lower = description.lower()

    best_category = "Miscellaneous"
    best_score = 0

    for category, keywords in SPENDING_CATEGORIES.items():
        for keyword in keywords:
            kw = keyword.lower()
            if kw in desc_lower:
                # Longer keyword match = more specific = better
                score = len(kw)
                if score > best_score:
                    best_score = score
                    best_category = category
                    break  # Found match in this category

    return best_category


def categorize_dataframe(df):
    """
    Add a 'category' column to a transactions DataFrame.
    Only categorizes rows that don't already have a category set.
    """
    import pandas as pd

    if "category" not in df.columns:
        df["category"] = ""

    mask = df["category"].isna() | (df["category"] == "")
    df.loc[mask, "category"] = df.loc[mask, "description"].apply(
        categorize_transaction
    )
    return df


def get_all_categories():
    """Return a sorted list of all spending category names."""
    return sorted(SPENDING_CATEGORIES.keys())
