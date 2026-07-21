"""
Basic statistical anomaly detection.

Two detectors, both non-AI (pure statistics), so they work whether or
not Gemini is configured — they're also used as the factual grounding
that gets handed to the LLM for recommendations/executive summaries,
so the AI is explaining real detected anomalies rather than inventing
plausible-sounding ones.
"""

import pandas as pd

from semantic_detector import get_primary_column


def detect_numeric_outliers(df: pd.DataFrame, max_columns: int = 5) -> list:
    """IQR-based outlier detection across up to `max_columns` numeric columns."""
    results = []
    numeric_cols = df.select_dtypes(include="number").columns.tolist()[:max_columns]

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 5:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = series[(series < lower) | (series > upper)]
        if len(outliers) == 0:
            continue
        results.append(
            {
                "column": col,
                "outlier_count": int(len(outliers)),
                "outlier_pct": round(len(outliers) / len(series) * 100, 2),
                "lower_bound": round(float(lower), 2),
                "upper_bound": round(float(upper), 2),
            }
        )
    return results


def detect_period_over_period_spikes(df: pd.DataFrame, semantic_columns: dict, threshold_pct: float = 30.0) -> list:
    """Flag month-over-month swings in revenue/sales beyond threshold_pct."""
    date_col = get_primary_column(semantic_columns, "date")
    value_col = get_primary_column(semantic_columns, "revenue") or get_primary_column(semantic_columns, "sales")
    if not date_col or not value_col:
        return []

    try:
        temp = df[[date_col, value_col]].copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")
        temp = temp.dropna()
        if temp.empty:
            return []

        monthly = temp.set_index(date_col).resample("MS")[value_col].sum()
        if len(monthly) < 2:
            return []

        pct_change = monthly.pct_change() * 100
        spikes = []
        for period, change in pct_change.dropna().items():
            if abs(change) >= threshold_pct:
                spikes.append(
                    {
                        "period": str(period.date()),
                        "column": value_col,
                        "change_pct": round(float(change), 2),
                        "direction": "increase" if change > 0 else "decrease",
                    }
                )
        return spikes
    except Exception:
        return []


def detect_anomalies(df: pd.DataFrame, semantic_columns: dict) -> dict:
    """Return {'numeric_outliers': [...], 'period_spikes': [...]}."""
    return {
        "numeric_outliers": detect_numeric_outliers(df),
        "period_spikes": detect_period_over_period_spikes(df, semantic_columns),
    }


def anomalies_to_text(anomalies: dict) -> str:
    """Render the anomaly dict as plain text for an LLM prompt."""
    lines = []
    for o in anomalies.get("numeric_outliers", []):
        lines.append(
            f"- {o['column']}: {o['outlier_count']} outliers ({o['outlier_pct']}% of values), "
            f"expected range {o['lower_bound']} to {o['upper_bound']}"
        )
    for s in anomalies.get("period_spikes", []):
        lines.append(f"- {s['column']} {s['direction']}d {abs(s['change_pct'])}% in {s['period']}")
    return "\n".join(lines) if lines else "No significant anomalies detected."
