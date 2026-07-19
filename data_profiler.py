"""
Dataset profiling: shape, column types, and missing-value summary.

This module is deliberately generic — it does not guess business
meaning (revenue, dates, etc.); that is semantic_detector's job.
"""

import pandas as pd


def profile_dataframe(df: pd.DataFrame) -> dict:
    """
    Build a profile summary for a DataFrame.

    Returns a dict with:
      - n_rows, n_columns
      - columns: list of {name, dtype, missing_count, missing_pct}
      - total_missing_cells, total_missing_pct
    """
    n_rows = len(df)
    n_columns = len(df.columns)

    columns = []
    total_missing = 0
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        total_missing += missing_count
        missing_pct = round((missing_count / n_rows) * 100, 2) if n_rows else 0.0
        columns.append(
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "missing_count": missing_count,
                "missing_pct": missing_pct,
            }
        )

    total_cells = n_rows * n_columns
    total_missing_pct = round((total_missing / total_cells) * 100, 2) if total_cells else 0.0

    return {
        "n_rows": n_rows,
        "n_columns": n_columns,
        "columns": columns,
        "total_missing_cells": total_missing,
        "total_missing_pct": total_missing_pct,
    }


def get_preview(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return the first n rows for display. Never raises on small/empty frames."""
    if df is None or df.empty:
        return df
    return df.head(min(n, len(df)))


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return describe() stats for numeric columns only. Empty DataFrame if none."""
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return pd.DataFrame()
    return numeric_df.describe().transpose()
