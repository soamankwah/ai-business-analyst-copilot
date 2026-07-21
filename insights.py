"""
AI-powered business insights.

Every function here returns (text, error) — never raises — so the UI
can render either the result or a clear "AI is disabled / failed"
message without a try/except at every call site. When AI isn't
configured, error is set to the same unavailable_reason() the sidebar
already shows, so the messaging is consistent app-wide.
"""

import os

import pandas as pd

from anomaly_detector import anomalies_to_text
from llm_client import LLMError, get_llm_client

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def _load_prompt(filename: str) -> str:
    with open(os.path.join(PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def _kpis_to_text(kpis: list) -> str:
    if not kpis:
        return "No KPIs were computed for this dataset."
    return "\n".join(f"- {k['label']}: {k['value']}" for k in kpis)


def _profile_to_text(profile: dict) -> str:
    lines = [
        f"- Rows: {profile['n_rows']:,}",
        f"- Columns: {profile['n_columns']:,}",
        f"- Missing data: {profile['total_missing_pct']}% of all cells",
    ]
    return "\n".join(lines)


def _run(template_name: str, **kwargs):
    client = get_llm_client()
    if not client.is_available():
        return None, client.unavailable_reason()
    template = _load_prompt(template_name)
    prompt = template.format(**kwargs)
    try:
        text = client.generate_text(prompt)
        return text, None
    except LLMError as e:
        return None, str(e)


def explain_kpis(kpis: list):
    """Plain-English explanation of the computed KPIs. Returns (text, error)."""
    return _run("insight_generation.txt", kpis=_kpis_to_text(kpis))


def generate_recommendations(kpis: list, anomalies: dict):
    """Three concrete recommendations grounded in KPIs + detected anomalies."""
    return _run("recommendations.txt", kpis=_kpis_to_text(kpis), anomalies=anomalies_to_text(anomalies))


def generate_executive_summary(profile: dict, kpis: list, anomalies: dict):
    """One-paragraph executive summary grounded in profile + KPIs + anomalies."""
    return _run(
        "executive_summary.txt",
        profile=_profile_to_text(profile),
        kpis=_kpis_to_text(kpis),
        anomalies=anomalies_to_text(anomalies),
    )


def explain_answer(question: str, result_df: pd.DataFrame):
    """Turn a SQL query result into a plain-English chat answer."""
    if result_df is None or result_df.empty:
        preview = "(no rows returned)"
    else:
        preview = result_df.head(10).to_string(index=False)
    return _run("answer_explanation.txt", question=question, result_preview=preview)
