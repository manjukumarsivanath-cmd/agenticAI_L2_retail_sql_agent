"""Integration tests - run against the real local MySQL database
(retail_agent_assignment, already seeded via database/load_data.py)."""

import pytest

from src.sql_tools import run_select


def test_run_select_returns_list_of_dicts():
    rows = run_select("SELECT store_id, region FROM stores LIMIT 3")
    assert isinstance(rows, list)
    assert len(rows) == 3
    for row in rows:
        assert isinstance(row, dict)
        assert "store_id" in row
        assert "region" in row


def test_run_select_blocks_unsafe_sql_before_hitting_db():
    with pytest.raises(ValueError):
        run_select("DELETE FROM stores")


def test_run_select_row_count_matches_loaded_data():
    rows = run_select("SELECT COUNT(*) AS n FROM stores")
    assert rows[0]["n"] == 15
