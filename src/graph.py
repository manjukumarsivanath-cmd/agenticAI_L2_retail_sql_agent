"""LangGraph StateGraph: generate SQL, execute it, summarize, update memory."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src import memory
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


def generate_sql(state: AgentState) -> dict:
    history_text = memory.format_history(state.get("history", []))
    prompt = f"""You are a MySQL expert. Given this schema:
{SCHEMA_DESCRIPTION}

Prior conversation, for resolving follow-up questions:
{history_text}

Write a single read-only MySQL SELECT statement to answer this question:
{state["question"]}

Return only the SQL statement. No explanation, no markdown formatting."""

    raw_sql = call_llm([{"role": "user", "content": prompt}])
    return {"sql": _strip_code_fences(raw_sql)}


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
    if not rows:
        return {"answer": "No data found for this question."}

    prompt = f"""Summarize this SQL result in 2-3 sentences of clear business language.
Only state facts present in the data below - do not invent numbers that aren't there.

Question: {state["question"]}
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
    graph.add_edge("generate_sql", "execute_sql")
    graph.add_edge("execute_sql", "summarize")
    graph.add_edge("summarize", "update_memory")
    graph.add_edge("update_memory", END)

    return graph.compile()
