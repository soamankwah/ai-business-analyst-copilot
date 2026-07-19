import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kpi_engine import compute_kpis
from semantic_detector import detect_semantic_columns


def _labels(kpis):
    return {k["label"] for k in kpis}


def test_kpis_include_revenue_and_margin_when_present():
    df = pd.DataFrame(
        {
            "Revenue": [100.0, 200.0],
            "Profit": [10.0, 40.0],
        }
    )
    semantic_columns = detect_semantic_columns(df)
    kpis = compute_kpis(df, semantic_columns)
    labels = _labels(kpis)
    assert "Total Revenue" in labels
    assert "Total Profit" in labels
    assert "Profit Margin" in labels


def test_kpis_include_churn_rate_with_yes_no_values():
    df = pd.DataFrame({"Churned": ["Yes", "No", "No", "No"]})
    semantic_columns = detect_semantic_columns(df)
    kpis = compute_kpis(df, semantic_columns)
    churn_kpi = next(k for k in kpis if k["label"] == "Churn Rate")
    assert churn_kpi["value"] == "25.0%"


def test_kpis_fallback_when_nothing_detected():
    df = pd.DataFrame({"random_col": [1, 2, 3]})
    semantic_columns = {k: [] for k in ["revenue", "sales", "date", "customer", "product", "region", "profit", "churn"]}
    kpis = compute_kpis(df, semantic_columns)
    labels = _labels(kpis)
    assert "Rows Loaded" in labels
    assert "Columns Loaded" in labels


def test_kpis_do_not_crash_on_missing_values():
    df = pd.DataFrame({"Revenue": [100.0, None, 300.0]})
    semantic_columns = detect_semantic_columns(df)
    kpis = compute_kpis(df, semantic_columns)
    assert any(k["label"] == "Total Revenue" for k in kpis)
