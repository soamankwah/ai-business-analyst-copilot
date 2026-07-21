"""
Semantic column detection.

Looks at column names (and, for numeric/date categories, the actual
values) to guess which columns represent revenue, sales, dates,
customers, products, regions, profit, and churn. This lets the KPI
and chart engines adapt to whatever dataset was uploaded instead of
assuming fixed column names.

Detection is intentionally simple (keyword matching + light type
validation) — no LLM call is involved, so this works with or without
Gemini configured.
"""

import re

import pandas as pd

CATEGORY_KEYWORDS = {
    "revenue": ["revenue", "total_sales", "sales_amount", "income", "gross_sales"],
    "sales": ["sales", "units_sold", "quantity", "orders", "order_count"],
    "date": ["date", "order_date", "period", "month", "year", "timestamp"],
    "customer": ["customer", "client", "user_id", "account_id", "buyer"],
    "product": ["product", "item", "sku", "category"],
    "region": ["region", "state", "country", "city", "location", "territory", "market"],
    "profit": ["profit", "margin", "net_income"],
    "churn": ["churn", "cancelled", "canceled", "attrition", "retention_status"],
}

# Order in which categories are checked when a column name matches
# more than one keyword set (first match wins for that column).
CATEGORY_PRIORITY = [
    "date",
    "revenue",
    "profit",
    "sales",
    "churn",
    "customer",
    "product",
    "region",
]


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower())


def _is_numeric_like(series: pd.Series, min_success_rate: float = 0.6) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    coerced = pd.to_numeric(series, errors="coerce")
    non_null = series.notna().sum()
    if non_null == 0:
        return False
    return (coerced.notna().sum() / non_null) >= min_success_rate


def _is_date_like(series: pd.Series, min_success_rate: float = 0.6) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    # A numeric column (e.g. a plain "Year" column with values like 2020)
    # will "successfully" parse via pd.to_datetime, because pandas treats
    # raw numbers as nanoseconds-since-epoch — producing bogus 1970-ish
    # timestamps rather than a real failure. Genuine date columns in
    # uploaded CSV/XLSX data are strings or already-parsed datetimes, not
    # bare integers/floats, so numeric columns are never treated as dates.
    if pd.api.types.is_numeric_dtype(series):
        return False

    try:
        coerced = pd.to_datetime(series, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        # Older pandas without format="mixed" support, or a genuinely
        # unparseable format — fall back to plain inference.
        try:
            coerced = pd.to_datetime(series, errors="coerce")
        except Exception:
            return False
    non_null = series.notna().sum()
    if non_null == 0:
        return False
    return (coerced.notna().sum() / non_null) >= min_success_rate


def detect_semantic_columns(df: pd.DataFrame) -> dict:
    """
    Return {category: [column_name, ...]} for the categories in
    CATEGORY_KEYWORDS. A column is assigned to at most one category
    (the highest-priority keyword match), and numeric/date categories
    additionally require the column's values to plausibly match that
    type — a column named "region_code" that's actually numeric IDs
    still won't be misfiled as a date, etc.
    """
    result = {category: [] for category in CATEGORY_KEYWORDS}

    for col in df.columns:
        norm = _normalize(col)
        matched_category = None
        for category in CATEGORY_PRIORITY:
            keywords = CATEGORY_KEYWORDS[category]
            if any(kw in norm for kw in keywords):
                matched_category = category
                break

        if matched_category is None:
            continue

        if matched_category == "date" and not _is_date_like(df[col]):
            continue
        if matched_category in ("revenue", "sales", "profit") and not _is_numeric_like(df[col]):
            continue

        result[matched_category].append(col)

    return result


def get_primary_column(semantic_columns: dict, category: str):
    """Return the first detected column for a category, or None."""
    cols = semantic_columns.get(category) or []
    return cols[0] if cols else None
