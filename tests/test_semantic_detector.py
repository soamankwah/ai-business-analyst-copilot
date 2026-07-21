import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from semantic_detector import detect_semantic_columns, get_primary_column


def test_detects_revenue_and_date_and_region():
    df = pd.DataFrame(
        {
            "Order_Date": ["2024-01-01", "2024-01-02"],
            "Revenue": [100, 200],
            "Region": ["North", "South"],
            "Customer_ID": [1, 2],
        }
    )
    result = detect_semantic_columns(df)
    assert "Order_Date" in result["date"]
    assert "Revenue" in result["revenue"]
    assert "Region" in result["region"]
    assert "Customer_ID" in result["customer"]


def test_does_not_misclassify_non_numeric_revenue_like_column():
    df = pd.DataFrame({"Revenue_Notes": ["high", "low", "medium"]})
    result = detect_semantic_columns(df)
    assert "Revenue_Notes" not in result["revenue"]


def test_does_not_misclassify_non_date_column_named_like_date():
    df = pd.DataFrame({"Date_Format_Type": ["ISO", "US", "EU"]})
    result = detect_semantic_columns(df)
    assert "Date_Format_Type" not in result["date"]


def test_get_primary_column_returns_first_or_none():
    semantic_columns = {"revenue": ["Revenue", "Sales_Amount"], "profit": []}
    assert get_primary_column(semantic_columns, "revenue") == "Revenue"
    assert get_primary_column(semantic_columns, "profit") is None
    assert get_primary_column(semantic_columns, "nonexistent") is None


def test_empty_dataframe_returns_empty_categories():
    df = pd.DataFrame()
    result = detect_semantic_columns(df)
    assert all(cols == [] for cols in result.values())


def test_does_not_misclassify_numeric_year_column_as_date():
    """
    Regression test: a plain integer 'Year' column (e.g. CarModelYear with
    values like 2020, 2021) must NOT be detected as a date. Pandas
    interprets raw numbers as nanoseconds-since-epoch, which "succeeds"
    but produces meaningless ~1970 timestamps rather than a real date.
    """
    df = pd.DataFrame({"CarModelYear": [2018, 2019, 2020, 2021, 2022]})
    result = detect_semantic_columns(df)
    assert "CarModelYear" not in result["date"]
