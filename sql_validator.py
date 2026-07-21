"""
SQL safety validation for AI-generated queries.

The LLM only ever proposes SQL — it never executes anything directly.
Every generated query passes through validate_sql() before it touches
DuckDB. This is a defensive allow-list (SELECT/WITH only, single
statement, references the expected table) rather than an attempt at
full SQL parsing — good enough to block DDL/DML and multi-statement
injection attempts from a text-generation model.
"""

import re

ALLOWED_START_KEYWORDS = ("select", "with")

FORBIDDEN_KEYWORDS = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "copy",
    "export",
    "import",
    "call",
    "execute",
    "grant",
    "revoke",
    "vacuum",
    "install",
    "load",
]


class SQLValidationError(Exception):
    """Raised when a generated SQL query fails safety validation."""


def _strip_code_fences(sql: str) -> str:
    cleaned = sql.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("sql"):
            cleaned = cleaned[3:]
    return cleaned.strip()


def validate_sql(sql: str, table_name: str) -> str:
    """
    Validate that `sql` is a single, read-only query against `table_name`.

    Returns the cleaned SQL string on success. Raises SQLValidationError
    with a specific reason on failure.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("The AI did not return a query.")

    cleaned = _strip_code_fences(sql)
    cleaned = cleaned.strip()

    # Only one statement: no semicolon except optionally a single
    # trailing one.
    body = cleaned[:-1] if cleaned.endswith(";") else cleaned
    if ";" in body:
        raise SQLValidationError("Multiple SQL statements are not allowed.")

    lowered = body.strip().lower()
    if not lowered.startswith(ALLOWED_START_KEYWORDS):
        raise SQLValidationError("Only SELECT or WITH queries are allowed.")

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise SQLValidationError(f"Query contains a disallowed keyword: '{keyword}'.")

    if table_name.lower() not in lowered:
        raise SQLValidationError(f"Query must reference the '{table_name}' table.")

    return body.strip()
