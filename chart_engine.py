"""
Automatic chart generation.

Picks up to three charts based on what semantic columns were detected
(date/revenue/sales/region/product/profit). Falls back to
generic, always-available charts (a numeric distribution, a
categorical breakdown) so the dashboard never ends up with fewer
than three charts, even for an unusual dataset.
"""

import pandas as pd
import plotly.express as px

from semantic_detector import get_primary_column


def _time_series_chart(df, semantic_columns):
    date_col = get_primary_column(semantic_columns, "date")
    value_col = get_primary_column(semantic_columns, "revenue") or get_primary_column(semantic_columns, "sales")
    if not date_col or not value_col:
        return None
    try:
        temp = df[[date_col, value_col]].copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")
        temp = temp.dropna()
        if temp.empty:
            return None
        monthly = temp.set_index(date_col).resample("MS")[value_col].sum().reset_index()
        fig = px.line(monthly, x=date_col, y=value_col, markers=True, title=f"{value_col} Over Time")
        return f"{value_col} Over Time", fig
    except Exception:
        return None


def _category_breakdown_chart(df, semantic_columns):
    value_col = get_primary_column(semantic_columns, "revenue") or get_primary_column(semantic_columns, "sales")
    group_col = get_primary_column(semantic_columns, "region") or get_primary_column(semantic_columns, "product")
    try:
        if group_col and value_col:
            temp = df[[group_col, value_col]].copy()
            temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")
            grouped = temp.groupby(group_col, dropna=True)[value_col].sum().sort_values(ascending=False).head(10)
            if grouped.empty:
                return None
            fig = px.bar(
                grouped.reset_index(), x=group_col, y=value_col, title=f"{value_col} by {group_col}"
            )
            return f"{value_col} by {group_col}", fig
        if group_col:
            counts = df[group_col].value_counts().head(10)
            if counts.empty:
                return None
            fig = px.bar(
                counts.rename_axis(group_col).reset_index(name="count"),
                x=group_col,
                y="count",
                title=f"Record Count by {group_col}",
            )
            return f"Record Count by {group_col}", fig
    except Exception:
        return None
    return None


def _distribution_chart(df, semantic_columns):
    col = (
        get_primary_column(semantic_columns, "profit")
        or get_primary_column(semantic_columns, "revenue")
        or get_primary_column(semantic_columns, "sales")
    )
    try:
        if col:
            values = pd.to_numeric(df[col], errors="coerce").dropna()
            if values.empty:
                return None
            fig = px.histogram(values, x=col, title=f"Distribution of {col}")
            return f"Distribution of {col}", fig
    except Exception:
        return None
    return None


def _fallback_numeric_chart(df, exclude_titles):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    for col in numeric_cols:
        title = f"Distribution of {col}"
        if title in exclude_titles:
            continue
        values = df[col].dropna()
        if values.empty:
            continue
        try:
            fig = px.histogram(values, x=col, title=title)
            return title, fig
        except Exception:
            continue
    return None


def _fallback_categorical_chart(df, exclude_titles):
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()
    for col in categorical_cols:
        title = f"Record Count by {col}"
        if title in exclude_titles:
            continue
        counts = df[col].value_counts().head(10)
        if counts.empty:
            continue
        try:
            fig = px.bar(counts.rename_axis(col).reset_index(name="count"), x=col, y="count", title=title)
            return title, fig
        except Exception:
            continue
    return None


def _fallback_schema_chart(df, exclude_titles):
    """Last-resort chart that always works: dtype composition of the dataset."""
    title = "Column Data Types"
    if title in exclude_titles:
        title = "Column Data Types (overview)"
    dtype_counts = df.dtypes.astype(str).value_counts().rename_axis("dtype").reset_index(name="count")
    fig = px.bar(dtype_counts, x="dtype", y="count", title=title)
    return title, fig


def generate_charts(df: pd.DataFrame, semantic_columns: dict) -> list:
    """
    Return up to 3 (title, plotly_figure) tuples for the dashboard.

    Tries semantic-aware charts first (time series, category
    breakdown, distribution); pads with generic fallback charts if
    the dataset doesn't have enough detected structure to reach 3.
    """
    charts = []
    seen_titles = set()

    for builder in (_time_series_chart, _category_breakdown_chart, _distribution_chart):
        result = builder(df, semantic_columns)
        if result and result[0] not in seen_titles:
            charts.append(result)
            seen_titles.add(result[0])

    fallback_builders = [
        lambda: _fallback_numeric_chart(df, seen_titles),
        lambda: _fallback_categorical_chart(df, seen_titles),
        lambda: _fallback_schema_chart(df, seen_titles),
    ]
    for builder in fallback_builders:
        if len(charts) >= 3:
            break
        result = builder()
        if result and result[0] not in seen_titles:
            charts.append(result)
            seen_titles.add(result[0])

    return charts[:3]
