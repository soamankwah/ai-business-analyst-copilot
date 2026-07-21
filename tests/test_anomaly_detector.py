import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly_detector import (
    anomalies_to_text,
    detect_anomalies,
    detect_numeric_outliers,
    detect_period_over_period_spikes,
)
from semantic_detector import detect_semantic_columns


def test_detect_numeric_outliers_finds_extreme_value():
    df = pd.DataFrame({"Revenue": [100, 105, 98, 102, 97, 101, 99, 5000]})
    outliers = detect_numeric_outliers(df)
    assert any(o["column"] == "Revenue" and o["outlier_count"] >= 1 for o in outliers)


def test_detect_numeric_outliers_empty_when_uniform():
    df = pd.DataFrame({"Revenue": [100, 101, 99, 100, 102, 98]})
    outliers = detect_numeric_outliers(df)
    assert outliers == []


def test_detect_numeric_outliers_skips_short_series():
    df = pd.DataFrame({"Revenue": [1, 2, 3]})
    outliers = detect_numeric_outliers(df)
    assert outliers == []


def test_detect_period_over_period_spikes_requires_date_and_value_columns():
    df = pd.DataFrame({"random": [1, 2, 3]})
    semantic_columns = {k: [] for k in ["revenue", "sales", "date", "customer", "product", "region", "profit", "churn"]}
    spikes = detect_period_over_period_spikes(df, semantic_columns)
    assert spikes == []


def test_detect_period_over_period_spikes_finds_jump():
    dates = pd.date_range("2024-01-01", periods=90, freq="D")
    revenue = [100] * 60 + [1000] * 30  # month 3 spikes hard vs months 1-2
    df = pd.DataFrame({"Order_Date": dates, "Revenue": revenue})
    semantic_columns = detect_semantic_columns(df)
    spikes = detect_period_over_period_spikes(df, semantic_columns, threshold_pct=30.0)
    assert len(spikes) >= 1
    assert spikes[0]["direction"] == "increase"


def test_detect_anomalies_returns_both_keys():
    df = pd.DataFrame({"Revenue": [100, 105, 98, 102, 97, 101, 99, 5000]})
    semantic_columns = detect_semantic_columns(df)
    result = detect_anomalies(df, semantic_columns)
    assert "numeric_outliers" in result
    assert "period_spikes" in result


def test_anomalies_to_text_handles_empty():
    text = anomalies_to_text({"numeric_outliers": [], "period_spikes": []})
    assert "no significant anomalies" in text.lower()


def test_anomalies_to_text_formats_outliers():
    anomalies = {
        "numeric_outliers": [
            {"column": "Revenue", "outlier_count": 2, "outlier_pct": 10.0, "lower_bound": 0, "upper_bound": 500}
        ],
        "period_spikes": [],
    }
    text = anomalies_to_text(anomalies)
    assert "Revenue" in text
    assert "2 outliers" in text
