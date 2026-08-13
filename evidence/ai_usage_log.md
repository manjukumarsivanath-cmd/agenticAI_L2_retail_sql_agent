# AI Usage Log

This project was built with Claude (Anthropic) as a coding assistant across an
interactive session. This log records what AI was used for, what the developer
did themselves, and the review process applied to AI output. Detailed bug
findings from that review are in `human_review_notes.md`, not repeated here.

## Division of work

**AI-assisted (drafted by Claude, reviewed and run by the developer before
acceptance):**
- `database/mysql_schema.sql`, `database/load_data.py`, `database/schema_reference.md`
- `src/config.py`, `src/tiger_gateway_client.py`, `src/safety.py`, `src/sql_tools.py`,
  `src/memory.py`, `src/graph.py`, `src/app.py`
- `tests/` (all 4 pytest files)
- `.gitignore`, `requirements.txt`, `pytest.ini`, `.env.example`
- This documentation (`README.md`, `evidence/`, `outputs/` summaries)

**Developer-driven decisions (AI presented options/tradeoffs, developer chose):**
- Model selection from the Tiger AI Gateway's ~90 available models - developer
  reviewed the model list and pricing table directly; final pick (`gpt-5-nano`)
  and the fallback candidate were a joint decision after weighing price tier,
  approval friction, and model generation.
- SQL safety approach - developer chose the stronger `sqlparse`-based parsing
  design over the Helper Guide's simpler regex baseline.
- Memory window size (5 turns) and the decision to explicitly document the
  $2 budget / 10,000 TPM constraint as the reasoning behind it.
- Whether to fix each bug found during testing vs. document it as a known
  limitation - the developer was asked and decided in each case (all were
  fixed).
- GitHub repository creation and all `git push` operations were performed by
  the developer directly, not by the AI assistant.

**Developer-only (AI never touched):**
- MySQL Server / Workbench installation (required IT helpdesk due to no local
  admin rights)
- Actually running the CLI app interactively and pasting real output back for
  review - all example conversations and test case results in this submission
  came from the developer running the agent themselves, not simulated by AI
- MySQL root password and Tiger AI Gateway API key - typed directly into
  `.env` by the developer, never shared in the AI conversation

## Review process

Every piece of AI-generated code or SQL was executed against real data (the
actual MySQL database, the actual Tiger AI Gateway) before being accepted, not
just visually reviewed. This surfaced 7 real bugs during development, all
documented with root cause and fix in `human_review_notes.md` - including one
directly relevant to the assignment's Responsible AI guardrail (a
destructive-intent request that initially produced a misleading summary
despite no data actually being modified).

## Responsible AI compliance

- Only the provided synthetic CSV data (`data/`) was used - no real customer,
  business, or confidential data was ever entered into any AI tool.
- No credentials, API keys, or passwords were pasted into the AI conversation
  at any point.
- All AI-generated SQL was validated against the actual schema and re-run
  after any correction, not assumed correct from a first draft.
