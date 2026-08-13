# Retail SQL Data Analyst Agent

A LangGraph-based agent that answers natural-language business questions about
retail sales data by generating safe, read-only MySQL queries, executing them,
and summarizing the results in business language. Built for the StackAI
Foundation Agentic AI Explorer - Level 2 assignment.

## Architecture

```
User question
      |
      v
generate_sql  --(destructive intent / CANNOT_COMPLY)--> summarize (refusal, no DB call)
      |                                                      ^
      |--(explainability question, e.g. "what data did      |
      |   you use?")-------------------------------------> update_memory (direct answer, no LLM/DB call)
      |
      v (normal case)
execute_sql (validates via safety.py, then runs against MySQL)
      |
      v
summarize (grounded in actual SQL + rows, or "no data" / error message)
      |
      v
update_memory (append turn to bounded conversation history)
      |
      v
Final answer
```

Implemented as a `langgraph.graph.StateGraph` in `src/graph.py`, with `AgentState`
carrying `question`, `history`, `sql`, `rows`, `answer`, and `error` between nodes.

## Project structure

```
data/                    Provided synthetic retail CSVs (stores, products, customers,
                          sales_transactions, returns)
database/
  mysql_schema.sql        CREATE TABLE statements for all 5 tables
  load_data.py             Loads the CSVs into MySQL, idempotent (re-runnable)
  schema_reference.md      Human-readable schema documentation
src/
  config.py                 Loads all env vars from .env
  tiger_gateway_client.py    Calls the Tiger AI Gateway (OpenAI-compatible chat API)
  safety.py                  SQL validation (SELECT-only) + destructive-intent detection
  sql_tools.py                Executes validated SQL, returns rows as dicts
  memory.py                    Bounded conversation history (last 5 turns)
  graph.py                      The LangGraph StateGraph itself
  app.py                         Interactive CLI
tests/                    pytest suite (40 tests, safety/sql_tools/memory/graph helpers)
outputs/                  Test case results, pytest summary, memory/follow-up evidence
evidence/                 AI usage log, architecture notes, human review notes
```

## Setup (Windows PowerShell)

### 1. Python virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. MySQL

Requires MySQL Server + MySQL Workbench (this project was built against MySQL
Server 8.4.9). With Workbench connected to your local server:

1. Open `database/mysql_schema.sql` in Workbench and execute the whole script
   (creates the `retail_agent_assignment` database and all 5 tables).
2. Load the data:
   ```powershell
   python database\load_data.py
   ```
   Prints row counts per table on success (expected: stores 15, products 10,
   customers 80, sales_transactions 360, returns 46 - matches the source CSVs
   exactly, re-running is safe since it clears and reloads each time).

### 3. Environment variables

Copy `.env.example` to `.env` and fill in the real values (never commit `.env` -
it's already gitignored):

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=retail_agent_assignment
MYSQL_USER=root
MYSQL_PASSWORD=<your MySQL root password>

TIGER_AI_GATEWAY_URL=https://api.ai-gateway.tigeranalytics.com
TIGER_AI_GATEWAY_API_KEY=<your Tiger AI Gateway API key>
TIGER_AI_GATEWAY_MODEL=gpt-5-nano
```

## Running the agent

```powershell
python src\app.py
```

Interactive loop - ask a question, type `exit` or `quit` to leave. Each turn
shows the generated SQL, any safety/error message, and the final answer.
Conversation history carries forward within the session (not across restarts).

Example:
```
You: Which region had the highest revenue?
SQL: SELECT s.region, SUM(...) AS revenue FROM sales_transactions st JOIN stores s ...
Answer: The North region had the highest revenue. The total revenue for North was 90,022.0125.

You: Now show only online channel
SQL: ... WHERE s.region = 'North' AND st.sales_channel = 'Online' ...
Answer: ...
```

## Running tests

```powershell
python -m pytest -v
```

40 tests covering SQL safety, SQL tool execution (integration, against the real
local database), memory/history behavior, and graph.py's deterministic routing
logic. `generate_sql`/`summarize` (the two LLM-calling nodes) are intentionally
not covered here, since automated tests hitting a paid API on every run would
be slow and burn real budget - their behavior is instead verified through the
manual evidence in `outputs/`.

## Design decisions

**Model: `gpt-5-nano` via Tiger AI Gateway.** Chosen from ~90 available models
for its Very Low price tier, newest-generation instruction-following (important
for reliable text-to-SQL), no extra approval friction, and an OpenAI-compatible
response shape confirmed via the gateway's Test Bench.

**Budget-aware design.** The AI Gateway's individual-usage tier caps usage at
**$2.00 total budget, 20 RPM, 10,000 TPM**. This directly shaped two decisions:
- Conversation memory is bounded to the **last 5 turns** (`src/memory.py`), not
  unbounded - every turn's history gets resent to the LLM on every question, so
  unlimited history would grow the prompt (and cost/latency) every turn.
- The graph avoids LLM calls wherever a deterministic answer is possible:
  destructive-intent refusals are caught by a keyword pre-check *before* any
  LLM call, and "what data did you use" style questions are answered directly
  from the previous turn's recorded SQL rather than issuing a fresh LLM call.
  A normal question costs at most 2 LLM calls (generate SQL + summarize).

**SQL safety, two layers.** `src/safety.py` uses `sqlparse` to properly parse
generated SQL (not just regex/prefix-matching) - requires exactly one statement,
confirms it's actually a `SELECT` via the parser's own statement-type detection,
and blocks a keyword list (including `outfile`/`dumpfile`, which block MySQL's
`SELECT ... INTO OUTFILE` file-write trick) as defense-in-depth. Separately,
`check_destructive_intent()` screens the *natural-language question itself* for
destructive intent (delete/update/drop/etc.) before any SQL is even generated -
this was added after testing showed the LLM could technically satisfy "Delete
all sales records" with a harmless-looking `SELECT COUNT(*)` while describing it
in a misleading way ("360 records are set to be deleted"). See
`evidence/human_review_notes.md` for the full bug and fix history.

## Known limitations

- Conversation memory does not persist across CLI restarts (in-memory only,
  per the assignment's scope).
- SQL generation is non-deterministic between runs (same question can produce
  differently-structured, though equally correct, SQL from one run to the next).
