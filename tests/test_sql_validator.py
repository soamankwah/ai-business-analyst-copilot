import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_validator import SQLValidationError, validate_sql


def test_allows_simple_select():
    sql = "SELECT * FROM business_data"
    assert validate_sql(sql, "business_data") == sql


def test_allows_with_clause():
    sql = "WITH t AS (SELECT * FROM business_data) SELECT * FROM t"
    assert validate_sql(sql, "business_data") == sql


def test_strips_trailing_semicolon():
    sql = "SELECT * FROM business_data;"
    assert validate_sql(sql, "business_data") == "SELECT * FROM business_data"


def test_strips_markdown_code_fences():
    sql = "```sql\nSELECT * FROM business_data\n```"
    assert validate_sql(sql, "business_data") == "SELECT * FROM business_data"


def test_rejects_insert():
    with pytest.raises(SQLValidationError):
        validate_sql("INSERT INTO business_data VALUES (1)", "business_data")


def test_rejects_drop():
    with pytest.raises(SQLValidationError):
        validate_sql("DROP TABLE business_data", "business_data")


def test_rejects_update():
    with pytest.raises(SQLValidationError):
        validate_sql("UPDATE business_data SET x = 1", "business_data")


def test_rejects_multiple_statements():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM business_data; DROP TABLE business_data", "business_data")


def test_rejects_query_not_referencing_expected_table():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM some_other_table", "business_data")


def test_rejects_empty_query():
    with pytest.raises(SQLValidationError):
        validate_sql("", "business_data")


def test_rejects_pragma():
    with pytest.raises(SQLValidationError):
        validate_sql("PRAGMA table_info('business_data')", "business_data")


def test_rejects_attach():
    with pytest.raises(SQLValidationError):
        validate_sql("ATTACH 'evil.db' AS x; SELECT * FROM business_data", "business_data")
