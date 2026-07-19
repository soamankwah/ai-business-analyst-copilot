"""
Central configuration for the AI Business Analyst Copilot.

Reads environment variables (via .env if present) and exposes constants
used across the app. Must be importable — and the app must be fully
usable — even when no Gemini credentials are configured.
"""

import os

from dotenv import load_dotenv

load_dotenv()  # no-op if there is no .env file; never raises

# --- AI provider configuration (Gemini) -------------------------------
# No model name is hard-coded anywhere in this app. Both values must
# come from the environment. If either is missing, AI features are
# disabled but the rest of the app runs normally.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip()

AI_ENABLED = bool(GEMINI_API_KEY) and bool(GEMINI_MODEL)

if not AI_ENABLED:
    AI_DISABLED_REASON = (
        "AI features are disabled. Set GEMINI_API_KEY and GEMINI_MODEL "
        "in your environment (see .env.example) to enable them."
    )
else:
    AI_DISABLED_REASON = ""

# --- File upload constraints -------------------------------------------
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = ("csv", "xlsx")

# --- DuckDB -------------------------------------------------------------
# Single table name used for the currently loaded dataset. No global
# shared connection is kept — connections are opened, used, and closed
# where needed (see data_loader.run_query).
DUCKDB_TABLE_NAME = "business_data"

# --- Sample dataset -------------------------------------------------------
SAMPLE_DATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "sample_datasets",
    "sample_retail_sales.csv",
)
SAMPLE_DATA_LABEL = "Sample: Retail Sales (bundled)"
