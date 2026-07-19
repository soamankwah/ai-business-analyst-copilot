"""
Data loading and ingestion.

Handles CSV/XLSX upload validation and loading, the bundled sample
dataset, and safe, short-lived DuckDB connections for querying a
DataFrame. No global/shared DuckDB connection is kept — a connection
is opened, used, and closed inside run_query().
"""

import os

import duckdb
import pandas as pd

import config


class FileValidationError(Exception):
    """Raised when an uploaded file fails validation."""


def validate_extension(filename: str) -> str:
    """Return the lowercase extension if allowed, else raise FileValidationError."""
    if not filename or "." not in filename:
        raise FileValidationError("File has no recognizable extension.")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        allowed = ", ".join(config.ALLOWED_EXTENSIONS)
        raise FileValidationError(f"Unsupported file type '.{ext}'. Allowed types: {allowed}.")
    return ext


def validate_size(size_bytes: int) -> None:
    """Raise FileValidationError if the file exceeds the configured max size."""
    if size_bytes is None:
        return  # size unknown — nothing to validate against
    max_bytes = config.MAX_FILE_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise FileValidationError(
            f"File is too large ({size_bytes / (1024 * 1024):.1f} MB). "
            f"Max allowed size is {config.MAX_FILE_SIZE_MB} MB."
        )


def _get_upload_size(uploaded_file) -> int:
    """Best-effort size lookup that works for Streamlit UploadedFile or file-like objects."""
    size = getattr(uploaded_file, "size", None)
    if size is not None:
        return size
    try:
        pos = uploaded_file.tell()
        uploaded_file.seek(0, os.SEEK_END)
        size = uploaded_file.tell()
        uploaded_file.seek(pos)
        return size
    except Exception:
        return None


def load_dataframe_from_upload(uploaded_file):
    """
    Validate and load an uploaded CSV/XLSX file into a DataFrame.

    `uploaded_file` is expected to expose `.name` and be file-like
    (readable by pandas) — this matches Streamlit's UploadedFile as
    well as a plain `io.BytesIO`/file object with a `.name` attribute
    set, which is what the unit tests use.

    Returns (dataframe, error_message). Exactly one of the two is None.
    """
    filename = getattr(uploaded_file, "name", None)
    try:
        ext = validate_extension(filename)
        validate_size(_get_upload_size(uploaded_file))

        if ext == "csv":
            df = pd.read_csv(uploaded_file)
        else:  # xlsx
            df = pd.read_excel(uploaded_file, engine="openpyxl")

        if df.empty:
            return None, "The uploaded file contains no data rows."
        if len(df.columns) == 0:
            return None, "The uploaded file has no columns."

        return df, None

    except FileValidationError as e:
        return None, str(e)
    except pd.errors.EmptyDataError:
        return None, "The uploaded file is empty or unreadable."
    except pd.errors.ParserError as e:
        return None, f"Could not parse the file as CSV: {e}"
    except Exception as e:  # noqa: BLE001 — surface any other read failure to the UI
        return None, f"Could not read the file: {e}"


def load_sample_dataset():
    """Load the bundled sample dataset. Returns (dataframe, error_message)."""
    try:
        df = pd.read_csv(config.SAMPLE_DATA_PATH)
        return df, None
    except Exception as e:  # noqa: BLE001
        return None, f"Could not load the sample dataset: {e}"


def run_query(df: pd.DataFrame, query: str, table_name: str = None) -> pd.DataFrame:
    """
    Register `df` as a DuckDB table and run a read query against it.

    Opens a fresh in-memory DuckDB connection, registers the DataFrame,
    executes the query, and always closes the connection — no shared
    global connection is used anywhere in the app.
    """
    table_name = table_name or config.DUCKDB_TABLE_NAME
    conn = duckdb.connect(database=":memory:")
    try:
        conn.register(table_name, df)
        return conn.execute(query).fetchdf()
    finally:
        conn.close()


def get_row_count(df: pd.DataFrame, table_name: str = None) -> int:
    """Convenience helper: row count of `df` as verified via a DuckDB round-trip."""
    table_name = table_name or config.DUCKDB_TABLE_NAME
    result = run_query(df, f"SELECT COUNT(*) AS n FROM {table_name}", table_name=table_name)
    return int(result["n"].iloc[0])
