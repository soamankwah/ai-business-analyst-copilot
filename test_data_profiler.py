import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_profiler import get_preview, numeric_summary, profile_dataframe


def test_profile_dataframe_basic():
    df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "z"]})
    profile = profile_dataframe(df)
    assert profile["n_rows"] == 3
    assert profile["n_columns"] == 2
    col_a = next(c for c in profile["columns"] if c["name"] == "a")
    assert col_a["missing_count"] == 1
    assert abs(col_a["missing_pct"] - 33.33) < 0.5


def test_get_preview_limits_rows():
    df = pd.DataFrame({"a": range(20)})
    preview = get_preview(df, 5)
    assert len(preview) == 5


def test_get_preview_handles_empty():
    df = pd.DataFrame()
    preview = get_preview(df, 5)
    assert preview.empty


def test_numeric_summary_only_numeric_columns():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    summary = numeric_summary(df)
    assert "a" in summary.index
    assert "b" not in summary.index


def test_numeric_summary_empty_when_no_numeric():
    df = pd.DataFrame({"b": ["x", "y", "z"]})
    summary = numeric_summary(df)
    assert summary.empty
