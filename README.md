# Narrative Risk Simulator

Retrieval-first PR copilot for sports communications teams. The app stress-tests a draft statement before publication by comparing it against a small corpus of prior statements, crisis examples, policy rules, sponsor guidelines, and recent narrative themes.

## What It Does
- Scores a draft from `0-100`.
- Breaks risk into `fan`, `sponsor`, `legal_policy`, and `media_escalation`.
- Returns the top 3 risk reasons.
- Assigns a verdict: `Safe to publish`, `Needs review`, or `Hold`.
- Shows retrieved evidence snippets.
- Rewrites the draft into safer wording.

## Stack
- `Streamlit` for the internal UI
- `OpenAI` for embeddings and analysis
- `Pydantic` for schemas and validation
- Local JSON seed files plus a local embedding cache under `data/cache/`

## Project Layout
- `app.py`: Streamlit entrypoint
- `src/narrative_risk/`: models, ingestion, indexing, retrieval, and analysis
- `data/seed/`: bundled demo corpus
- `tests/`: unit tests for ingestion, retrieval, and analyzer behavior

## Setup
1. Create a virtual environment if needed:

```bash
uv venv
```

2. Install dependencies:

```bash
uv sync --group dev
```

3. Copy the environment template:

```bash
cp .env.example .env
```

4. Edit `.env` and provide your API key. The file supports:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Shell environment variables still take precedence over `.env` values if both are present.

## Run
```bash
uv run streamlit run app.py
```

## Supported Uploads
- `txt`
- `md`
- `csv`
- `json`

CSV uploads must include:
- `title`
- `source_type`
- `body`

Optional CSV columns:
- `date`
- `tags`
- `summary`
- `risk_notes`

For `txt` and `md` uploads, the UI captures the source type and can optionally override the title.

## Seed Corpus
The bundled corpus includes:
- public-style sports statements
- crisis and backlash examples with notes on what went wrong
- sponsor and legal/policy guidance
- a trend snapshot summarizing active media narratives

This makes the app usable on first launch without enterprise integrations.

## Demo Flow
1. Launch the app.
2. Paste a draft sponsor announcement, apology, executive quote, or press statement.
3. Optionally upload your own text-based source docs.
4. Run the simulation.
5. Review the score, axis breakdown, evidence, and rewritten draft.

## Validation
Run the test suite with:

```bash
uv run pytest -q
```
