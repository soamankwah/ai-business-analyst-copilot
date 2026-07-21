import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import query_engine
from query_engine import ask_question, build_schema_description


class _FakeClient:
    def __init__(self, response_text, available=True):
        self._response_text = response_text
        self._available = available

    def is_available(self):
        return self._available

    def unavailable_reason(self):
        return "AI features are disabled for this test."

    def generate_text(self, prompt):
        return self._response_text


@pytest.fixture
def sample_df():
    return pd.DataFrame({"Region": ["North", "South"], "Revenue": [100, 200]})


def test_build_schema_description_lists_all_columns(sample_df):
    schema = build_schema_description(sample_df)
    assert "Region" in schema
    assert "Revenue" in schema


def test_ask_question_returns_error_when_ai_disabled(monkeypatch, sample_df):
    monkeypatch.setattr(query_engine, "get_llm_client", lambda: _FakeClient("", available=False))
    result = ask_question(sample_df, "What is total revenue?")
    assert result["success"] is False
    assert result["error"]
    assert result["sql"] is None


def test_ask_question_runs_valid_generated_sql(monkeypatch, sample_df):
    monkeypatch.setattr(
        query_engine, "get_llm_client", lambda: _FakeClient("SELECT SUM(Revenue) AS total FROM business_data")
    )
    result = ask_question(sample_df, "What is total revenue?")
    assert result["success"] is True
    assert result["error"] is None
    assert result["result_df"]["total"].iloc[0] == 300


def test_ask_question_rejects_unsafe_generated_sql(monkeypatch, sample_df):
    monkeypatch.setattr(
        query_engine, "get_llm_client", lambda: _FakeClient("DROP TABLE business_data")
    )
    result = ask_question(sample_df, "Delete everything")
    assert result["success"] is False
    assert "rejected for safety" in result["error"].lower()


def test_ask_question_rejects_empty_question(monkeypatch, sample_df):
    monkeypatch.setattr(
        query_engine, "get_llm_client", lambda: _FakeClient("SELECT * FROM business_data")
    )
    result = ask_question(sample_df, "   ")
    assert result["success"] is False
    assert "enter a question" in result["error"].lower()


def test_ask_question_surfaces_execution_error(monkeypatch, sample_df):
    monkeypatch.setattr(
        query_engine, "get_llm_client", lambda: _FakeClient("SELECT nonexistent_column FROM business_data")
    )
    result = ask_question(sample_df, "Show me a column that doesn't exist")
    assert result["success"] is False
    assert result["sql"] is not None
