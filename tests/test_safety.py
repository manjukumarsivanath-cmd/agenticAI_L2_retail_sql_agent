import pytest

from src.safety import REFUSAL_MESSAGE, check_destructive_intent, validate_sql


class TestValidateSql:
    def test_allows_simple_select(self):
        assert validate_sql("SELECT * FROM stores") == "SELECT * FROM stores"

    def test_strips_trailing_semicolon(self):
        assert validate_sql("SELECT * FROM stores;") == "SELECT * FROM stores"

    def test_rejects_empty_sql(self):
        with pytest.raises(ValueError):
            validate_sql("")

    @pytest.mark.parametrize(
        "bad_sql",
        [
            "DROP TABLE stores",
            "DELETE FROM stores",
            "UPDATE stores SET city='X'",
            "INSERT INTO stores VALUES ('x','y','z','w','v')",
            "TRUNCATE TABLE stores",
            "ALTER TABLE stores ADD COLUMN x INT",
        ],
    )
    def test_blocks_write_statements(self, bad_sql):
        with pytest.raises(ValueError):
            validate_sql(bad_sql)

    def test_blocks_stacked_statements(self):
        with pytest.raises(ValueError):
            validate_sql("SELECT * FROM stores; DROP TABLE stores")

    def test_blocks_into_outfile(self):
        with pytest.raises(ValueError):
            validate_sql("SELECT * FROM stores INTO OUTFILE '/tmp/x.csv'")

    def test_strips_comments_before_checking(self):
        with pytest.raises(ValueError):
            validate_sql("SELECT * FROM stores; /* sneaky */ DROP TABLE stores")


class TestCheckDestructiveIntent:
    @pytest.mark.parametrize(
        "question",
        [
            "Delete all sales records.",
            "Please remove the returns table.",
            "Update store city for ST-001.",
            "Can you drop the customers table?",
        ],
    )
    def test_flags_destructive_questions(self, question):
        assert check_destructive_intent(question) == REFUSAL_MESSAGE

    @pytest.mark.parametrize(
        "question",
        [
            "Which region had the highest revenue?",
            "Show top 5 product categories by revenue.",
            "Compare online and in-store revenue.",
        ],
    )
    def test_allows_read_only_questions(self, question):
        assert check_destructive_intent(question) is None
