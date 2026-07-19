import io
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from data_loader import (
    FileValidationError,
    get_row_count,
    load_dataframe_from_upload,
    load_sample_dataset,
    run_query,
    validate_extension,
    validate_size,
)


def _make_upload(name, content_bytes):
    buf = io.BytesIO(content_bytes)
    buf.name = name
    return buf


def test_validate_extension_allows_csv_and_xlsx():
    assert validate_extension("data.csv") == "csv"
    assert validate_extension("data.xlsx") == "xlsx"


def test_validate_extension_rejects_other_types():
    with pytest.raises(FileValidationError):
        validate_extension("data.json")


def test_validate_extension_rejects_missing_extension():
    with pytest.raises(FileValidationError):
        validate_extension("data")


def test_validate_size_within_limit():
    validate_size(1024)  # should not raise


def test_validate_size_over_limit_raises():
    too_big = (config.MAX_FILE_SIZE_MB + 1) * 1024 * 1024
    with pytest.raises(FileValidationError):
        validate_size(too_big)


def test_load_dataframe_from_upload_csv():
    content = b"a,b\n1,2\n3,4\n"
    upload = _make_upload("test.csv", content)
    df, error = load_dataframe_from_upload(upload)
    assert error is None
    assert list(df.columns) == ["a", "b"]
    assert len(df) == 2


def test_load_dataframe_from_upload_rejects_bad_extension():
    upload = _make_upload("test.txt", b"a,b\n1,2\n")
    df, error = load_dataframe_from_upload(upload)
    assert df is None
    assert "Unsupported file type" in error


def test_load_dataframe_from_upload_empty_file():
    upload = _make_upload("test.csv", b"a,b\n")
    df, error = load_dataframe_from_upload(upload)
    assert df is None
    assert "no data rows" in error


def test_load_sample_dataset():
    df, error = load_sample_dataset()
    assert error is None
    assert df is not None
    assert len(df) > 0


def test_run_query_and_row_count():
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = run_query(df, "SELECT COUNT(*) AS n FROM business_data")
    assert int(result["n"].iloc[0]) == 3
    assert get_row_count(df) == 3
