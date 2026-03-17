---
name: write-tests
description: Enforce test creation and maintenance for code changes in this repository. Use when implementing features, fixing bugs, refactoring behavior, or editing production code so Codex adds or updates pytest coverage, runs the relevant validation, and documents any unavoidable test gap before finishing.
---

# Write Tests

Require a test plan for every behavior change. Mirror the repository's current pytest style, keep coverage focused on the changed behavior, and do not close the task with undocumented test gaps.

## Workflow

1. Identify the behavior surface before editing code.
Map the changed file to its most likely test module. In this repo, application code under `src/narrative_risk/` is typically covered by `tests/test_<module>.py`.

2. Add or update tests in the same change.
Create the smallest useful automated coverage that proves the new or changed behavior. For a bug fix, include a regression test that fails without the fix. For a new feature, cover the expected success path and the most relevant failure or edge path.

3. Reuse the existing test style.
Prefer plain pytest tests with local fakes and in-memory fixtures. Follow the current pattern of short, explicit test functions and avoid introducing new test frameworks, network calls, or unnecessary mocking layers.

4. Cover the right cases.
Include only cases that materially protect the change:
- Happy path for the intended behavior
- One failure, invalid-input, or boundary case when the code can fail
- A regression case when fixing a reported defect
- Serialization, parsing, or schema checks when the change alters structured data

5. Run validation before finishing.
Start with the smallest relevant command, then widen only if needed. For this repo, use `uv run pytest -q tests/test_<module>.py` for targeted verification and `uv run pytest -q` when the change affects shared behavior or multiple modules.

6. Report any remaining gap explicitly.
If an automated test is not practical, say why, describe the manual validation you performed, and leave a concrete note about what is still unverified. Do not claim coverage or validation that did not happen.

## Repository Conventions

- Keep tests under `tests/`.
- Match file names to the production module when practical, for example `src/narrative_risk/ingest.py` to `tests/test_ingest.py`.
- Prefer deterministic fixtures and hard-coded sample payloads over external files unless the behavior specifically depends on file loading.
- Assert user-visible outcomes and structured return values rather than internal implementation details.
- Avoid broad snapshot-style assertions when a few precise assertions would prove the behavior more clearly.

## Done Criteria

- The code change and the relevant test change land together.
- The executed validation command is reported accurately.
- Any skipped or missing automated test is called out explicitly.
