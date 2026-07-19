"""
KPI computation.

Builds a list of KPI cards from whatever semantic columns were
detected in the uploaded dataset. Every KPI is computed defensively —
one failing computation (bad data, unexpected values) never breaks
the others or the app.
"""

import pandas as pd

from semantic_detector import get_primary_column

TRUE_TOKENS = {"1", "true", "yes", "y", "churned", "cancelled", "canceled"}
FALSE_TOKENS = {"0", "false", "no", "n", "active", "retained"}


def _format_currency(value: float) -> str:
    return f"${value:,.2f}"


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"


def _to_boolean_series(series: pd.Series) -> pd.Series:
    """Best-effort conversion of a churn-like column to booleans."""
    if pd.api.types.is_bool_dtype(series):
        return series
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).astype(float) != 0
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.map(lambda v: True if v in TRUE_TOKENS else (False if v in FALSE_TOKENS else None))


def compute_kpis(df: pd.DataFrame, semantic_columns: dict) -> list:
    """
    Return a list of {"label": str, "value": str} KPI cards.

    Only includes KPIs for which the underlying columns were detected —
    a dataset with no date column simply won't produce a date-range KPI,
    rather than erroring or showing a placeholder.
    """
    kpis = []

    revenue_col = get_primary_column(semantic_columns, "revenue")
    sales_col = get_primary_column(semantic_columns, "sales")
    profit_col = get_primary_column(semantic_columns, "profit")
    customer_col = get_primary_column(semantic_columns, "customer")
    product_col = get_primary_column(semantic_columns, "product")
    region_col = get_primary_column(semantic_columns, "region")
    date_col = get_primary_column(semantic_columns, "date")
    churn_col = get_primary_column(semantic_columns, "churn")

    if revenue_col:
        try:
            total_revenue = pd.to_numeric(df[revenue_col], errors="coerce").sum()
            kpis.append({"label": "Total Revenue", "value": _format_currency(total_revenue)})
        except Exception:
            pass

    if sales_col:
        try:
            total_sales = pd.to_numeric(df[sales_col], errors="coerce").sum()
            kpis.append({"label": "Total Units / Sales", "value": _format_number(total_sales)})
        except Exception:
            pass

    if profit_col:
        try:
            total_profit = pd.to_numeric(df[profit_col], errors="coerce").sum()
            kpis.append({"label": "Total Profit", "value": _format_currency(total_profit)})
            if revenue_col:
                rev_sum = pd.to_numeric(df[revenue_col], errors="coerce").sum()
                if rev_sum:
                    margin = (total_profit / rev_sum) * 100
                    kpis.append({"label": "Profit Margin", "value": f"{margin:.1f}%"})
        except Exception:
            pass

    if customer_col:
        try:
            kpis.append({"label": "Unique Customers", "value": _format_number(df[customer_col].nunique())})
        except Exception:
            pass

    if product_col:
        try:
            kpis.append({"label": "Unique Products", "value": _format_number(df[product_col].nunique())})
        except Exception:
            pass

    if region_col:
        try:
            kpis.append({"label": "Regions Covered", "value": _format_number(df[region_col].nunique())})
        except Exception:
            pass

    if date_col:
        try:
            parsed = pd.to_datetime(df[date_col], errors="coerce").dropna()
            if not parsed.empty:
                span_days = (parsed.max() - parsed.min()).days
                date_range = f"{parsed.min().date()} to {parsed.max().date()}"
                kpis.append({"label": "Date Range", "value": date_range})
                kpis.append({"label": "Days Covered", "value": _format_number(span_days)})
        except Exception:
            pass

    if churn_col:
        try:
            bool_series = _to_boolean_series(df[churn_col]).dropna()
            if not bool_series.empty:
                churn_rate = (bool_series.sum() / len(bool_series)) * 100
                kpis.append({"label": "Churn Rate", "value": f"{churn_rate:.1f}%"})
        except Exception:
            pass

    if not kpis:
        kpis.append({"label": "Rows Loaded", "value": _format_number(len(df))})
        kpis.append({"label": "Columns Loaded", "value": _format_number(len(df.columns))})

    return kpis
