# Release Log

Use one line per shipped change.

| Date | Branch | Commit | Type | Summary | AI Tool | AI Usage | Human Check | Validation | Client Impact | Rollback | Defect Found |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-03-11 | feat/narrative-risk-simulator | uncommitted | docs | Add a simple product overview document covering purpose, current POC features, future additions, and market gap. | codex | docs | self-verified | Manual review of markdown content; no code or dependency changes, so Snyk scan not required. | Easier stakeholder understanding of the product concept and roadmap. | Remove the overview document and release log entry. | none |
| 2026-03-12 | feat/narrative-risk-simulator | uncommitted | feat | Redesign the Streamlit interface to clarify the sports communications risk-review workflow and improve the results presentation. | codex | design,code | self-verified | `uv run pytest -q`; manual code review of the Streamlit layout; Snyk scan attempted separately before closeout. | First-time users can understand the product purpose faster and scan verdicts, evidence, and rewrites more easily. | Revert the `app.py` UI refresh and remove this release log entry. | none |
| 2026-03-12 | feat/narrative-risk-simulator | uncommitted | docs | Add a project-local `write-tests` skill that requires pytest coverage or documented validation gaps for code changes. | codex | design,docs | self-verified | Initialized the skill scaffold, reviewed repo test conventions, and validated the skill structure with `.venv/bin/python .../quick_validate.py`. | Future AI-assisted changes are less likely to ship without matching tests or explicit validation notes. | Remove `skills/write-tests` and this release log entry. | none |
