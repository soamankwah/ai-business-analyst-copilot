import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chart_engine import generate_charts
from semantic_detector import detect_semantic_columns


def test_generate_charts_returns_three_for_rich_dataset():
    df = pd.DataFrame(
        {
            "Order_Date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "Region": ["North", "South"] * 15,
            "Revenue": list(range(30)),
            "Profit": list(range(0, 60, 2)),
        }
    )
    semantic_columns = detect_semantic_columns(df)
    charts = generate_charts(df, semantic_columns)
    assert len(charts) == 3
    for title, fig in charts:
        assert isinstance(title, str) and title
        assert fig is not None


def test_generate_charts_falls_back_for_minimal_dataset():
    df = pd.DataFrame({"random_number": [1, 2, 3, 4, 5]})
    semantic_columns = {k: [] for k in ["revenue", "sales", "date", "customer", "product", "region", "profit", "churn"]}
    charts = generate_charts(df, semantic_columns)
    assert len(charts) >= 1
    for title, fig in charts:
        assert fig is not None


def test_generate_charts_no_duplicate_titles():
    df = pd.DataFrame(
        {
            "Region": ["North", "South", "East"],
            "Revenue": [100, 200, 300],
        }
    )
    semantic_columns = detect_semantic_columns(df)
    charts = generate_charts(df, semantic_columns)
    titles = [t for t, _ in charts]
    assert len(titles) == len(set(titles))
