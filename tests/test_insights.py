import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import insights


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


SAMPLE_KPIS = [{"label": "Total Revenue", "value": "$1,000.00"}]
SAMPLE_ANOMALIES = {"numeric_outliers": [], "period_spikes": []}
SAMPLE_PROFILE = {"n_rows": 10, "n_columns": 3, "total_missing_pct": 0.0}


def test_explain_kpis_returns_error_when_ai_disabled(monkeypatch):
    monkeypatch.setattr(insights, "get_llm_client", lambda: _FakeClient("", available=False))
    text, error = insights.explain_kpis(SAMPLE_KPIS)
    assert text is None
    assert error


def test_explain_kpis_returns_text_when_available(monkeypatch):
    monkeypatch.setattr(insights, "get_llm_client", lambda: _FakeClient("Revenue looks healthy."))
    text, error = insights.explain_kpis(SAMPLE_KPIS)
    assert error is None
    assert text == "Revenue looks healthy."


def test_generate_recommendations_returns_text(monkeypatch):
    monkeypatch.setattr(insights, "get_llm_client", lambda: _FakeClient("1. Do X.\n2. Do Y.\n3. Do Z."))
    text, error = insights.generate_recommendations(SAMPLE_KPIS, SAMPLE_ANOMALIES)
    assert error is None
    assert "Do X" in text


def test_generate_executive_summary_returns_text(monkeypatch):
    monkeypatch.setattr(insights, "get_llm_client", lambda: _FakeClient("Overall, the business is stable."))
    text, error = insights.generate_executive_summary(SAMPLE_PROFILE, SAMPLE_KPIS, SAMPLE_ANOMALIES)
    assert error is None
    assert "stable" in text


def test_explain_answer_handles_empty_result(monkeypatch):
    monkeypatch.setattr(insights, "get_llm_client", lambda: _FakeClient("No matching rows were found."))
    text, error = insights.explain_answer("How many rows match X?", pd.DataFrame())
    assert error is None
    assert "No matching rows" in text


def test_explain_answer_returns_error_when_ai_disabled(monkeypatch):
    monkeypatch.setattr(insights, "get_llm_client", lambda: _FakeClient("", available=False))
    result_df = pd.DataFrame({"total": [300]})
    text, error = insights.explain_answer("What is total revenue?", result_df)
    assert text is None
    assert error
