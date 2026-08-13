"""SQL safety validation: only single, read-only SELECT statements are allowed."""

import re

import sqlparse

BLOCKED_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate", "create",
    "replace", "grant", "revoke", "lock", "call", "execute", "outfile",
    "dumpfile",
]

DESTRUCTIVE_INTENT_KEYWORDS = [
    "delete", "remove", "drop", "truncate", "update", "insert", "modify",
    "erase", "wipe", "alter",
]

REFUSAL_MESSAGE = (
    "This agent only answers read-only questions using SELECT queries. "
    "It cannot delete, update, insert, or otherwise modify data."
)


def check_destructive_intent(question: str) -> str | None:
    """Catch write/destructive intent in the user's natural-language question,
    before an LLM call is ever made. Returns a refusal message, or None if the
    question looks read-only."""
    lowered = question.lower()
    for word in DESTRUCTIVE_INTENT_KEYWORDS:
        if re.search(rf"\b{word}\b", lowered):
            return REFUSAL_MESSAGE
    return None


def validate_sql(sql: str) -> str:
    if not sql or not sql.strip():
        raise ValueError("Empty SQL is not allowed.")

    cleaned = sqlparse.format(sql, strip_comments=True).strip()
    statements = [s for s in sqlparse.parse(cleaned) if str(s).strip()]

    if len(statements) != 1:
        raise ValueError("Only a single SQL statement is allowed.")

    statement = statements[0]
    if statement.get_type() != "SELECT":
        raise ValueError("Only SELECT queries are allowed.")

    statement_text = str(statement).strip().rstrip(";")
    lowered = statement_text.lower()
    for word in BLOCKED_KEYWORDS:
        if re.search(rf"\b{word}\b", lowered):
            raise ValueError(f"Blocked keyword detected: {word}")

    return statement_text
