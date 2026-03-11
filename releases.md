# Release Log

Use one line per shipped change.

| Date | Branch | Commit | Type | Summary | AI Tool | AI Usage | Human Check | Validation | Client Impact | Rollback | Defect Found |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-03-10 | feat/narrative-risk-simulator | uncommitted | feat | Add a Streamlit retrieval-first PR risk simulator POC with seeded corpus, local embedding cache, and tests. | codex | code | self-verified | `pytest -q`, import smoke; Snyk scan unavailable because the MCP call was rejected. | Internal demo app for pre-release communications risk review. | Revert the feature branch changes. | none |
| 2026-03-11 | feat/narrative-risk-simulator | uncommitted | feat | Add `.env`-based configuration loading with a tracked template, shared config helpers, and tests for precedence/defaults. | codex | code | self-verified | `.venv/bin/python -m pytest -q`, `.venv/bin/python -c "import app"`; Snyk scan unavailable because the MCP call was rejected. | Local setup no longer requires shell exports for OpenAI configuration. | Revert the `.env` support changes on the feature branch. | none |
