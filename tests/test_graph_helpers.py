"""Tests for graph.py's deterministic helper functions - not generate_sql/summarize,
which make real paid LLM calls and don't belong in an automated test suite."""

from src.graph import (
    _is_empty_result,
    _strip_code_fences,
    _tables_used_in,
    is_explainability_question,
    route_after_generate_sql,
)


class TestIsEmptyResult:
    def test_empty_list_is_empty(self):
        assert _is_empty_result([]) is True

    def test_single_all_none_row_is_empty(self):
        assert _is_empty_result([{"total": None}]) is True

    def test_single_row_with_value_is_not_empty(self):
        assert _is_empty_result([{"total": 0}]) is False

    def test_multiple_rows_not_empty(self):
        assert _is_empty_result([{"a": 1}, {"a": 2}]) is False


class TestTablesUsedIn:
    def test_finds_known_tables(self):
        sql = "SELECT * FROM stores JOIN sales_transactions ON stores.store_id = sales_transactions.store_id"
        assert set(_tables_used_in(sql)) == {"stores", "sales_transactions"}

    def test_single_table(self):
        assert _tables_used_in("SELECT * FROM products") == ["products"]

    def test_no_tables_found(self):
        assert _tables_used_in("SELECT 1") == []


class TestIsExplainabilityQuestion:
    def test_matches_known_phrasing(self):
        assert is_explainability_question("What data did you use for this answer?")

    def test_does_not_match_normal_question(self):
        assert not is_explainability_question("Which region had the highest revenue?")


class TestStripCodeFences:
    def test_strips_sql_fence(self):
        text = "```sql\nSELECT 1\n```"
        assert _strip_code_fences(text) == "SELECT 1"

    def test_leaves_plain_text_untouched(self):
        assert _strip_code_fences("SELECT 1") == "SELECT 1"


class TestRouteAfterGenerateSql:
    def test_routes_to_execute_sql_normally(self):
        assert route_after_generate_sql({"sql": "SELECT 1"}) == "execute_sql"

    def test_routes_to_summarize_on_error(self):
        assert route_after_generate_sql({"error": "blocked"}) == "summarize"

    def test_routes_to_update_memory_on_direct_answer(self):
        assert route_after_generate_sql({"answer": "explanation"}) == "update_memory"
