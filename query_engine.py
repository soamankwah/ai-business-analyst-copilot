"""
Natural-language querying of the uploaded dataset.

Flow: question + schema -> LLM generates SQL -> sql_validator checks
it's a safe read-only query against the expected table -> executed via
data_loader.run_query() (fresh DuckDB connection, opened and closed
per call, per Phase 1's rule).

Fully inert when AI isn't configured: ask_question() returns a
structured "unavailable" result rather than raising, so the UI can
show a clear message instead of crashing.
"""

import os

import pandas as pd

import config
from data_loader import run_query
from llm_client import LLMError, get_llm_client
from sql_validator import SQLValidationError, validate_sql

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def _load_prompt(filename: str) -> str:
    with open(os.path.join(PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def build_schema_description(df: pd.DataFrame) -> str:
    return "\n".join(f"- {col} ({df[col].dtype})" for col in df.columns)


def ask_question(df: pd.DataFrame, question: str, table_name: str = None) -> dict:
    """
    Answer a natural-language question about `df` by generating and
    running SQL.

    Returns a dict:
      {"success": bool, "sql": str|None, "result_df": DataFrame|None, "error": str|None}
    """
    table_name = table_name or config.DUCKDB_TABLE_NAME
    client = get_llm_client()

    if not client.is_available():
        return {"success": False, "sql": None, "result_df": None, "error": client.unavailable_reason()}

    if not question or not question.strip():
        return {"success": False, "sql": None, "result_df": None, "error": "Please enter a question."}

    template = _load_prompt("sql_generation.txt")
    prompt = template.format(table=table_name, schema=build_schema_description(df), question=question.strip())

    try:
        raw_sql = client.generate_text(prompt)
    except LLMError as e:
        return {"success": False, "sql": None, "result_df": None, "error": str(e)}

    try:
        validated_sql = validate_sql(raw_sql, table_name)
    except SQLValidationError as e:
        return {"success": False, "sql": raw_sql, "result_df": None, "error": f"Generated query was rejected for safety: {e}"}

    try:
        result_df = run_query(df, validated_sql, table_name=table_name)
    except Exception as e:  # noqa: BLE001 — surface DuckDB errors (bad column, syntax) to the UI
        return {"success": False, "sql": validated_sql, "result_df": None, "error": f"Query execution failed: {e}"}

    return {"success": True, "sql": validated_sql, "result_df": result_df, "error": None}
