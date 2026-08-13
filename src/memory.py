"""Bounded conversation memory so follow-up questions can reference recent turns.

Window is capped at MAX_TURNS (not the full conversation) to stay within the
AI Gateway's 10,000 TPM limit and $2 budget - each turn's history gets resent
to the LLM on every question, so unbounded history would grow the prompt
(and cost/latency) on every single turn.
"""

MAX_TURNS = 5


def add_turn(history: list[dict], question: str, sql: str, answer: str) -> list[dict]:
    updated = history + [{"question": question, "sql": sql, "answer": answer}]
    return updated[-MAX_TURNS:]


def format_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    turns = [
        f"Q: {turn['question']}\nSQL: {turn['sql']}\nA: {turn['answer']}"
        for turn in history
    ]
    return "\n\n".join(turns)
