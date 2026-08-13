"""LangGraph StateGraph: generate SQL, execute it, summarize, update memory."""

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src import memory
from src.safety import REFUSAL_MESSAGE, check_destructive_intent
from src.sql_tools import run_select
from src.tiger_gateway_client import call_llm

SCHEMA_DESCRIPTION = """
stores(store_id, store_name, region, city, store_type)
products(product_id, product_name, category, sub_category, base_price)
customers(customer_id, customer_segment, signup_date, preferred_channel, city)
sales_transactions(order_id, order_date, store_id, product_id, customer_id,
    sales_channel, units_sold, unit_price, discount_pct, payment_status, delivery_status)
returns(return_id, order_id, return_date, return_reason)

Foreign keys: sales_transactions.store_id -> stores.store_id,
sales_transactions.product_id -> products.product_id,
sales_transactions.customer_id -> customers.customer_id,
returns.order_id -> sales_transactions.order_id.

There is no "amount" or "sales" column/table. Total sale value for a row is:
units_sold * unit_price * (1 - discount_pct / 100)
"""

KNOWN_TABLES = ["stores", "products", "customers", "sales_transactions", "returns"]

EXPLAINABILITY_PATTERNS = [
    "what data did you use",
    "what data was used",
    "what tables did you use",
    "what fields did you use",
    "what data are you using",
    "how did you get this",
    "how did you calculate",
    "explain your answer",
    "explain how you got",
    "where does this data come from",
    "what did you use for this",
]


class AgentState(TypedDict):
    question: str
    history: list[dict]
    sql: str
    rows: list[dict]
    answer: str
    error: str | None


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def is_explainability_question(question: str) -> bool:
    lowered = question.lower()
    return any(pattern in lowered for pattern in EXPLAINABILITY_PATTERNS)


def _tables_used_in(sql: str) -> list[str]:
    lowered = sql.lower()
    return [table for table in KNOWN_TABLES if re.search(rf"\b{table}\b", lowered)]


def _is_empty_result(rows: list[dict]) -> bool:
    if not rows:
        return True
    # SUM/AVG over zero matching rows returns one row of NULLs, not an empty list.
    if len(rows) == 1 and all(value is None for value in rows[0].values()):
        return True
    return False


def generate_sql(state: AgentState) -> dict:
    # Deterministic pre-check, catches obvious destructive intent with zero LLM cost.
    refusal = check_destructive_intent(state["question"])
    if refusal:
        return {"sql": "", "error": refusal}

    history = state.get("history", [])

    if is_explainability_question(state["question"]):
        if not history:
            return {
                "sql": "",
                "answer": "There's no previous answer yet to explain - ask a data question first.",
                "error": None,
            }
        last_turn = history[-1]
        tables = _tables_used_in(last_turn["sql"])
        explanation = (
            f'For the previous answer ("{last_turn["question"]}"), I queried '
            f"the following table(s): {', '.join(tables) if tables else 'none identified'}. "
            f"The exact SQL run was: {last_turn['sql']}"
        )
        return {"sql": "", "answer": explanation, "error": None}

    history_text = memory.format_history(history)
    last_sql = history[-1]["sql"] if history else None
    follow_up_note = ""
    if last_sql:
        follow_up_note = f"""
If, and only if, the current question explicitly narrows or modifies the previous
one using words like "now", "only", "just", "instead", or "what about", keep the
existing filters/conditions from the most recent SQL query below and add the new
condition on top of them.

If instead the current question asks something new and independent - a different
grouping, metric, or topic, with no such narrowing language - answer it fresh
against the full dataset. Do NOT carry over filters from the previous query in
that case, even though the conversation history is shown to you for context.

Most recent SQL query:
{last_sql}
"""

    prompt = f"""You are a MySQL expert. Given this schema:
{SCHEMA_DESCRIPTION}

Prior conversation, for resolving follow-up questions:
{history_text}
{follow_up_note}
Write a single read-only MySQL SELECT statement to answer this question:
{state["question"]}

Rules:
- Return only the SQL statement. No explanation, no markdown formatting.
- Always include the actual metric/value being asked about (e.g. the revenue
  figure, the count) as an output column - never select only an identifying
  column (like region or product name) and drop the number behind ORDER BY
  where the user can't see it.
- If answering this would require inserting, updating, deleting, or otherwise
  modifying data or schema, do not write a workaround SELECT (e.g. do not count
  or preview what would be changed). Instead respond with exactly: CANNOT_COMPLY"""

    raw_sql = call_llm([{"role": "user", "content": prompt}])
    sql = _strip_code_fences(raw_sql)

    # LLM-level backstop for destructive intent the keyword pre-check missed.
    if sql.strip().upper().startswith("CANNOT_COMPLY"):
        return {"sql": "", "error": REFUSAL_MESSAGE}

    return {"sql": sql}


def route_after_generate_sql(state: AgentState) -> str:
    if state.get("answer"):
        return "update_memory"
    return "summarize" if state.get("error") else "execute_sql"


def execute_sql(state: AgentState) -> dict:
    try:
        rows = run_select(state["sql"])
        return {"rows": rows, "error": None}
    except Exception as exc:
        return {"rows": [], "error": str(exc)}


def summarize(state: AgentState) -> dict:
    if state.get("error"):
        return {"answer": f"I can't run that request: {state['error']}"}

    rows = state.get("rows", [])
    if _is_empty_result(rows):
        return {"answer": "No data found for this question."}

    prompt = f"""Summarize this SQL result in 2-3 sentences of clear business language.
The SQL query below has already applied every filter and grouping needed to answer
the question - do not claim a dimension (e.g. channel, region) is missing just
because it isn't one of the output columns; it may have been filtered on instead
of selected. Only state facts present in the data below - do not invent numbers
that aren't there.

Question: {state["question"]}
SQL used: {state["sql"]}
Data: {rows}"""

    answer = call_llm([{"role": "user", "content": prompt}])
    return {"answer": answer}


def update_memory(state: AgentState) -> dict:
    updated_history = memory.add_turn(
        state.get("history", []), state["question"], state.get("sql", ""), state["answer"]
    )
    return {"history": updated_history}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("summarize", summarize)
    graph.add_node("update_memory", update_memory)

    graph.add_edge(START, "generate_sql")
    graph.add_conditional_edges(
        "generate_sql",
        route_after_generate_sql,
        {
            "execute_sql": "execute_sql",
            "summarize": "summarize",
            "update_memory": "update_memory",
        },
    )
    graph.add_edge("execute_sql", "summarize")
    graph.add_edge("summarize", "update_memory")
    graph.add_edge("update_memory", END)

    return graph.compile()
