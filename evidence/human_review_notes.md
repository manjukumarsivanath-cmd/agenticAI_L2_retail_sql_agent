# Human Review Notes

Per the assignment's Human-in-the-Loop requirement, every piece of AI-generated
SQL, code, and business-language output in this project was executed and
reviewed by hand before being accepted - not just read, but actually run
against the real local MySQL database and Tiger AI Gateway, with results
checked for correctness, safety, and grounding. This document records what was
found during that review, including the real bugs caught and fixed.

## Review process

For each component, the pattern was: draft the code, explain the design
rationale, run it against real data/queries, and inspect the actual output
before moving on. Several rounds of testing surfaced genuine bugs - each one is
recorded below with what was observed, the root cause, the fix, and how the fix
was re-verified.

## Issues found and fixed

### 1. Misleading response to a destructive request (critical - SQL Safety)

**Observed:** Asking "Delete all sales records" did not get refused. The agent
wrote a technically-safe `SELECT COUNT(*) FROM sales_transactions` (which
`safety.py` correctly allowed, since it genuinely is read-only), but the
summarization step then described it as *"The delete operation for all sales
records is configured to remove 360 rows... 360 sales records are set to be
deleted."* No data was touched, but the wording was actively misleading - it
reads as though a deletion happened or was staged.

**Root cause:** `generate_sql`'s prompt told the model to write a SELECT for
any question, so for a destructive request it reinterpreted "delete" as "count
what would be deleted" instead of refusing outright.

**Fix:** Two-layer defense. (1) `safety.check_destructive_intent()` - a
deterministic keyword pre-check on the raw natural-language question, runs
*before* any LLM call, catching the obvious case at zero cost. (2)
`generate_sql`'s prompt also instructs the LLM to respond with the exact
sentinel `CANNOT_COMPLY` for destructive intent it detects itself, as a
backstop for phrasing the keyword list might miss. `graph.py`'s
`route_after_generate_sql` then skips `execute_sql` entirely and routes
straight to a refusal message.

**Re-verified:** "Delete all sales records" now produces no SQL at all and an
immediate, accurate refusal message.

### 2. Follow-up answer contradicted its own SQL

**Observed:** Asking "Now show only online channel" right after a
region-ranking question produced SQL that correctly added
`WHERE sales_channel = 'online'`, but the summarized answer claimed *"The data
provided does not include any channel breakdown, so online-channel figures
cannot be reported"* - directly contradicting the query that had just run.

**Root cause:** `summarize()` only received the *result rows* (which didn't
include a channel column, since it wasn't selected - the filter happened in the
`WHERE` clause, not the output columns), not the SQL that produced them, so it
had no way to know filtering had already occurred.

**Fix:** Pass `state["sql"]` into the summarize prompt as well, with an
explicit instruction not to claim a dimension is missing just because it isn't
an output column.

**Re-verified:** the same style of follow-up now correctly acknowledges the
filter that was applied.

### 3. "No data" case not reliably detected

**Observed:** "Show sales for year 2035" happened to produce a correct "no
data" style answer, but only because the LLM noticed a `NULL` in the result on
its own - not because the code detected it.

**Root cause:** `SUM()`/`AVG()` over zero matching rows returns one row of
`NULL`s in SQL, not an empty row list, so the original `if not rows:` check
never actually fired.

**Fix:** Added `_is_empty_result()`, which also treats a single row where every
value is `None` as "no data."

**Re-verified:** now deterministic regardless of whether the LLM happens to
notice the `NULL`.

### 4. Follow-up dropped a previously-applied filter

**Observed:** After "Show sales for South region" then "Now show only online
channel," the second answer reported the *global* online-channel total, not
South-region-online. The South filter was silently dropped.

**Root cause:** the prompt gave prior conversation as reference text but never
explicitly instructed the model to preserve the previous query's filters when
answering a follow-up.

**Fix:** added an explicit instruction: when the question uses narrowing
language ("now", "only", "just", "instead", "what about"), keep the existing
filters from the most recent SQL and add the new condition on top.

**Re-verified:** the same sequence now correctly produces
`WHERE region='South' AND sales_channel='Online'`.

### 5. Regression: the fix for #4 over-applied to fresh questions

**Observed:** Immediately after fixing #4, "Summarize revenue and returns by
category" - a fresh, independent question with no narrowing language - asked
right after the South+Online follow-up chain, incorrectly inherited those
filters. Revenue figures came back scoped to South+Online instead of the full
dataset, which is not what "summarize by category" should mean absent any
narrowing language.

**Root cause:** the instruction added for #4 didn't distinguish between "this
is clearly a refinement" and "this is a new question that happens to follow in
the same session."

**Fix:** tightened the rule to only preserve filters when explicit narrowing
language is present, and to explicitly reset to the full dataset for
independent questions.

**Re-verified:** re-ran the exact same South → Online → category-summary
sequence; the category summary now exactly matches the unfiltered totals from
an earlier, independent run of the same question (e.g. Groceries revenue
116,329.80 in both), confirming no filter leakage.

### 6. Explainability question answered with fabricated context

**Observed:** "What data did you use for this answer?" produced a plausible
but disconnected answer - it ran a fresh `COUNT(*)` across all 5 tables
(including `customers`), when the actual previous answer never touched
`customers` at all.

**Root cause:** there was no real introspection - the question was treated as
a brand-new data question rather than a request to explain the *previous*
turn's actual query.

**Fix:** added `is_explainability_question()` to detect this question pattern
and, when matched, skip SQL generation/execution entirely - the graph instead
inspects `history[-1]["sql"]` directly and reports the real tables used
(`_tables_used_in()`), grounded in what actually ran.

**Re-verified:** the table list now correctly varies depending on what the
immediately preceding query actually joined (confirmed it correctly excludes
`stores` or `customers` in different runs, matching the real prior SQL).

### 7. "Top N" queries sometimes hid the actual number

**Observed:** "Which region had the highest revenue?" occasionally produced
SQL that wrapped the aggregation in a subquery and only selected the
identifying column (`region`), dropping `total_revenue` from the output - the
model then had to admit "the exact amount isn't shown."

**Fix:** added an explicit prompt rule requiring the actual metric/value to
always be included as an output column, not buried behind `ORDER BY` alone.

**Re-verified:** the same question now reliably includes the revenue figure.

## Responsible AI confirmation

- Only the provided synthetic CSV data was used throughout development and
  testing.
- No credentials, API keys, or passwords were pasted into any AI tool - the
  Tiger AI Gateway key and MySQL password were typed directly into `.env` by
  the developer, never shared in conversation.
- All SQL, prompts, and generated code shown above were executed and read by a
  human before being accepted, and every bug listed was found through that
  review, not assumed away.
