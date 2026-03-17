from __future__ import annotations

import html
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from narrative_risk.analyze import NarrativeRiskAnalyzer
from narrative_risk.config import INDEX_PATH, has_openai_api_key
from narrative_risk.index import EmbeddingIndex
from narrative_risk.ingest import parse_uploaded_documents
from narrative_risk.models import AnalysisResult, Document, RetrievedEvidence, SourceType, Verdict
from narrative_risk.retrieve import retrieve_evidence
from narrative_risk.seed import load_seed_documents


st.set_page_config(page_title="Narrative Risk Simulator", layout="wide")


VERDICT_STYLES = {
    Verdict.SAFE_TO_PUBLISH: {
        "label": "Safe to publish",
        "class_name": "safe",
        "summary": "Low narrative risk based on the current evidence set.",
    },
    Verdict.NEEDS_REVIEW: {
        "label": "Needs review",
        "class_name": "review",
        "summary": "Usable draft, but the framing needs tighter approval before release.",
    },
    Verdict.HOLD: {
        "label": "Hold",
        "class_name": "hold",
        "summary": "High likelihood of backlash, escalation, or policy conflict if published now.",
    },
}

SCORE_LEGEND = [
    ("0-39", "Safe to publish", "Low concern. Publish with standard comms review."),
    ("40-69", "Needs review", "Moderate concern. Tighten tone, claims, or context before release."),
    ("70-100", "Hold", "High concern. Rework messaging and escalate to comms, sponsor, or legal leads."),
]

WORKFLOW_STEPS = [
    ("1", "Paste draft", "Review a sponsor announcement, apology, press release, or executive quote."),
    ("2", "Compare against evidence", "Cross-check against statements, crisis examples, policy rules, sponsor guidance, and trend snapshots."),
    ("3", "Review safer wording", "Get a score, narrative risk explanation, and a safer alternative draft."),
]

BENEFIT_CHIPS = [
    "Fan backlash risk",
    "Sponsor and partner pressure",
    "Legal, policy, and media escalation",
]

SUPPORTED_SOURCES = [
    "Prior statements",
    "Crisis cases",
    "Policy rules",
    "Sponsor guidance",
    "Narrative trends",
]

SAMPLE_DRAFTS = [
    "Sponsor announcement with a sensitive category",
    "Executive quote during an active investigation",
    "Apology statement after public backlash",
    "Policy or event announcement with fan impact",
]


@st.cache_resource(show_spinner=False)
def bootstrap_index() -> EmbeddingIndex:
    return EmbeddingIndex(index_path=INDEX_PATH)


@st.cache_data(show_spinner=False)
def seed_documents() -> list[dict[str, object]]:
    return [document.model_dump(mode="json") for document in load_seed_documents()]


def main() -> None:
    inject_styles()
    render_hero()
    render_workflow()

    if not has_openai_api_key():
        st.warning("Set `OPENAI_API_KEY` in your shell or `.env` file before running a full analysis.")

    workspace_left, workspace_right = st.columns([1.45, 0.95], gap="large")

    with workspace_left:
        draft, upload_source_type, title_override, uploads, run_analysis = render_input_panel()

    with workspace_right:
        render_preflight_panel()

    if not run_analysis:
        render_empty_results()
        return

    if not draft.strip():
        st.error("A draft statement is required.")
        return
    if not has_openai_api_key():
        st.error("Set `OPENAI_API_KEY` in your shell or `.env` file before running the simulator.")
        return

    uploaded_documents: list[Document] = []
    for upload in uploads or []:
        try:
            uploaded_documents.extend(
                parse_uploaded_documents(
                    upload.name,
                    upload.getvalue(),
                    default_source_type=upload_source_type,
                    title_override=title_override or None,
                )
            )
        except ValueError as exc:
            st.error(f"{upload.name}: {exc}")
            return

    try:
        index = bootstrap_index()
        combined_documents = load_documents() + uploaded_documents
        indexed_count = index.sync_documents(combined_documents)
        evidence = retrieve_evidence(index, draft)
        result = NarrativeRiskAnalyzer().analyze(draft, evidence)
    except Exception as exc:  # pragma: no cover - UI level fallback
        st.exception(exc)
        return

    render_results(result=result, draft=draft, indexed_count=indexed_count)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #09111f;
            --bg-2: #101d31;
            --surface: rgba(246, 244, 238, 0.97);
            --surface-muted: rgba(255, 255, 255, 0.08);
            --surface-line: rgba(255, 255, 255, 0.14);
            --text: #08101e;
            --ink-soft: #41506a;
            --ink-inverse: #f8f5ee;
            --accent: #c7a76c;
            --accent-strong: #e0c284;
            --safe: #0f8a5f;
            --review: #b97812;
            --hold: #b13a32;
            --shadow: 0 22px 60px rgba(4, 10, 24, 0.28);
            --radius: 24px;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(199, 167, 108, 0.18), transparent 30%),
                radial-gradient(circle at top right, rgba(52, 80, 125, 0.28), transparent 28%),
                linear-gradient(180deg, #08101e 0%, #0b1526 42%, #0d1728 100%);
        }

        [data-testid="stAppViewContainer"] > .main {
            color: var(--ink-inverse);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1380px;
        }

        h1, h2, h3 {
            font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
            letter-spacing: -0.02em;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.4rem 0.8rem;
            border: 1px solid rgba(224, 194, 132, 0.28);
            border-radius: 999px;
            background: rgba(199, 167, 108, 0.12);
            color: var(--accent-strong);
            font-size: 0.8rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 1rem;
        }

        .hero-card,
        .panel-card,
        .result-card,
        .evidence-card,
        .legend-card,
        .empty-card {
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .hero-card {
            padding: 2.25rem 2.35rem 2rem;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02)),
                linear-gradient(140deg, rgba(19, 35, 60, 0.92), rgba(8, 16, 30, 0.96));
            border: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: 1.4rem;
        }

        .hero-title {
            margin: 0;
            font-size: clamp(2.4rem, 4vw, 4.2rem);
            line-height: 0.95;
            color: var(--ink-inverse);
            max-width: 11ch;
        }

        .hero-copy {
            margin: 1rem 0 1.4rem;
            max-width: 62rem;
            color: rgba(248, 245, 238, 0.8);
            font-size: 1.05rem;
            line-height: 1.7;
        }

        .chip-row,
        .workflow-grid,
        .legend-list,
        .source-row {
            display: grid;
            gap: 0.85rem;
        }

        .chip-row {
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        }

        .hero-chip,
        .source-pill {
            padding: 0.9rem 1rem;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            background: rgba(255, 255, 255, 0.05);
            color: rgba(248, 245, 238, 0.92);
            font-size: 0.95rem;
        }

        .workflow-grid {
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            margin-bottom: 1.6rem;
        }

        .workflow-card {
            padding: 1.2rem 1.1rem;
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .workflow-step {
            width: 2rem;
            height: 2rem;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: rgba(199, 167, 108, 0.18);
            border: 1px solid rgba(199, 167, 108, 0.32);
            color: var(--accent-strong);
            font-weight: 700;
            margin-bottom: 0.8rem;
        }

        .workflow-card h3,
        .panel-card h3,
        .result-card h3,
        .legend-card h3,
        .empty-card h3,
        .evidence-card h3 {
            margin: 0;
            color: var(--ink-inverse);
            font-size: 1.2rem;
        }

        .workflow-card p,
        .workflow-note,
        .panel-copy,
        .legend-copy,
        .empty-copy {
            color: rgba(248, 245, 238, 0.76);
            line-height: 1.65;
            margin: 0.55rem 0 0;
        }

        .source-row {
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        }

        .panel-card,
        .legend-card,
        .empty-card,
        .result-card,
        .evidence-card {
            padding: 1.45rem 1.35rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .section-title {
            font-size: 0.82rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: rgba(224, 194, 132, 0.92);
            margin: 0 0 0.65rem;
        }

        .panel-divider {
            height: 1px;
            background: rgba(255, 255, 255, 0.12);
            margin: 1rem 0 1.1rem;
        }

        .legend-list {
            grid-template-columns: 1fr;
        }

        .legend-row {
            display: grid;
            grid-template-columns: 88px 1fr;
            gap: 0.9rem;
            padding: 0.85rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        .legend-row:last-child {
            border-bottom: none;
        }

        .legend-band {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: fit-content;
            padding: 0.45rem 0.65rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            color: var(--accent-strong);
            font-weight: 700;
        }

        .legend-label {
            color: var(--ink-inverse);
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .legend-detail,
        .bullet-list li,
        .sample-list li {
            color: rgba(248, 245, 238, 0.78);
            line-height: 1.55;
        }

        .bullet-list,
        .sample-list {
            margin: 0;
            padding-left: 1.1rem;
        }

        .result-section {
            margin-top: 1.75rem;
        }

        .verdict-banner {
            padding: 1.5rem 1.6rem;
            border-radius: 26px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.03)),
                rgba(255, 255, 255, 0.04);
            margin-bottom: 1rem;
        }

        .verdict-banner.safe {
            box-shadow: inset 0 0 0 1px rgba(15, 138, 95, 0.22);
        }

        .verdict-banner.review {
            box-shadow: inset 0 0 0 1px rgba(185, 120, 18, 0.22);
        }

        .verdict-banner.hold {
            box-shadow: inset 0 0 0 1px rgba(177, 58, 50, 0.22);
        }

        .verdict-kicker {
            display: inline-flex;
            padding: 0.35rem 0.65rem;
            border-radius: 999px;
            font-size: 0.76rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }

        .verdict-banner.safe .verdict-kicker {
            background: rgba(15, 138, 95, 0.18);
            color: #8ee3c0;
        }

        .verdict-banner.review .verdict-kicker {
            background: rgba(185, 120, 18, 0.18);
            color: #f2cb7a;
        }

        .verdict-banner.hold .verdict-kicker {
            background: rgba(177, 58, 50, 0.18);
            color: #f3a29b;
        }

        .verdict-grid,
        .metric-grid {
            display: grid;
            gap: 1rem;
        }

        .verdict-grid {
            grid-template-columns: minmax(220px, 320px) 1fr;
            align-items: end;
        }

        .score-big {
            font-size: clamp(3rem, 7vw, 5rem);
            line-height: 0.9;
            color: var(--ink-inverse);
            margin: 0;
        }

        .score-caption,
        .verdict-summary {
            color: rgba(248, 245, 238, 0.76);
            margin: 0.25rem 0 0;
            line-height: 1.6;
        }

        .metric-grid {
            grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            margin: 1rem 0 1.25rem;
        }

        .metric-card {
            padding: 1rem 1.05rem;
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.09);
        }

        .metric-label {
            color: rgba(248, 245, 238, 0.72);
            font-size: 0.88rem;
            margin-bottom: 0.5rem;
        }

        .metric-value {
            color: var(--ink-inverse);
            font-size: 2rem;
            line-height: 1;
            font-weight: 700;
        }

        .result-card {
            height: 100%;
        }

        .result-card .body-text,
        .evidence-meta,
        .evidence-body {
            color: rgba(248, 245, 238, 0.8);
            line-height: 1.65;
        }

        .reason-list,
        .narrative-list {
            margin: 0.85rem 0 0;
            padding-left: 1.1rem;
        }

        .reason-list li,
        .narrative-list li {
            margin-bottom: 0.55rem;
            color: rgba(248, 245, 238, 0.82);
            line-height: 1.55;
        }

        .evidence-card {
            margin-bottom: 0.9rem;
        }

        .evidence-topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.55rem;
        }

        .evidence-tag {
            display: inline-flex;
            padding: 0.35rem 0.6rem;
            border-radius: 999px;
            background: rgba(224, 194, 132, 0.14);
            color: var(--accent-strong);
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .rewrite-box {
            padding: 1.1rem;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.09);
            color: rgba(248, 245, 238, 0.9);
            line-height: 1.7;
            white-space: pre-wrap;
        }

        .stTextArea textarea,
        .stTextInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stFileUploader section {
            border-radius: 18px !important;
        }

        .stTextArea textarea,
        .stTextInput input {
            background: rgba(255, 255, 255, 0.97) !important;
            color: var(--text) !important;
        }

        .stButton > button {
            border-radius: 999px;
            min-height: 3rem;
            background: linear-gradient(135deg, #d6b57b, #b98b3e);
            color: #111827;
            border: none;
            font-weight: 700;
        }

        .stButton > button:hover {
            background: linear-gradient(135deg, #e2c88c, #c79848);
            color: #0b1220;
        }

        @media (max-width: 960px) {
            .hero-card {
                padding: 1.6rem;
            }

            .verdict-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    chips = "".join(f"<div class='hero-chip'>{html.escape(chip)}</div>" for chip in BENEFIT_CHIPS)
    st.markdown(
        f"""
        <section class="hero-card">
            <div class="eyebrow">Sports Communications Control Room</div>
            <h1 class="hero-title">Pressure-test a public statement before it becomes tomorrow's headline.</h1>
            <p class="hero-copy">
                Narrative Risk Simulator helps sports communications teams review draft statements before publication.
                It checks a message against prior statements, crisis cases, policies, sponsor guidance, and current
                narrative themes so comms leads can spot backlash risk early and tighten the wording before release.
            </p>
            <div class="chip-row">{chips}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_workflow() -> None:
    workflow_cards = "".join(
        (
            "<div class='workflow-card'>"
            f"<div class='workflow-step'>{html.escape(step_number)}</div>"
            f"<h3>{html.escape(title)}</h3>"
            f"<p>{html.escape(copy)}</p>"
            "</div>"
        )
        for step_number, title, copy in WORKFLOW_STEPS
    )
    source_pills = "".join(f"<div class='source-pill'>{html.escape(source)}</div>" for source in SUPPORTED_SOURCES)
    st.markdown(
        f"""
        <div class="workflow-grid">{workflow_cards}</div>
        <p class="workflow-note">Evidence sources used during simulation</p>
        <div class="source-row">{source_pills}</div>
        """,
        unsafe_allow_html=True,
    )


def render_input_panel() -> tuple[str, SourceType, str, list[object] | None, bool]:
    st.markdown(
        """
        <div class="panel-card">
            <p class="section-title">Draft Workspace</p>
            <h3>Prepare the statement you want to stress-test.</h3>
            <p class="panel-copy">
                Paste the draft exactly as your team would send it for review. Add optional source material if you
                want the simulator to compare the draft against custom evidence during this run.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='panel-divider'></div>", unsafe_allow_html=True)

    draft = st.text_area(
        "Draft statement",
        height=300,
        placeholder="Paste a sponsor announcement, apology, executive quote, or press release.",
    )
    st.markdown("**Supporting uploads**")
    upload_source_type = st.selectbox(
        "Source type for TXT/MD uploads",
        options=list(SourceType),
        format_func=format_source_type,
    )
    title_override = st.text_input("Optional title override for TXT/MD uploads")
    uploads = st.file_uploader(
        "Upload TXT, MD, CSV, or JSON evidence files",
        accept_multiple_files=True,
        type=["txt", "md", "csv", "json"],
        help="CSV files must include title, source_type, and body columns.",
    )
    run_analysis = st.button("Run Narrative Risk Simulation", type="primary", use_container_width=True)
    return draft, upload_source_type, title_override, uploads, run_analysis


def render_preflight_panel() -> None:
    legend_rows = "".join(
        (
            "<div class='legend-row'>"
            f"<div class='legend-band'>{html.escape(score_range)}</div>"
            "<div>"
            f"<div class='legend-label'>{html.escape(label)}</div>"
            f"<div class='legend-detail'>{html.escape(detail)}</div>"
            "</div>"
            "</div>"
        )
        for score_range, label, detail in SCORE_LEGEND
    )
    sample_items = "".join(f"<li>{html.escape(item)}</li>" for item in SAMPLE_DRAFTS)
    st.markdown(
        f"""
        <div class="legend-card">
            <p class="section-title">How To Read The Score</p>
            <h3>Verdict bands used by the simulator</h3>
            <p class="legend-copy">
                The app produces a single headline score and four risk-axis scores. Use the verdict band to decide
                whether the draft is ready, needs a tighter review loop, or should be held back entirely.
            </p>
            <div class="legend-list">{legend_rows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="empty-card" style="margin-top: 1rem;">
            <p class="section-title">Best Fit</p>
            <h3>Draft types this screen is built for</h3>
            <p class="empty-copy">
                Keep the language sports-specific and publication-ready. The strongest analyses come from real draft
                statements, not bullet notes.
            </p>
            <ul class="sample-list">{sample_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_results() -> None:
    st.markdown("<div class='result-section'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.0, 1.0], gap="large")
    with left:
        st.markdown(
            """
            <div class="empty-card">
                <p class="section-title">What You Get</p>
                <h3>Clear signals before anything is published</h3>
                <p class="empty-copy">
                    Run the simulation to see an overall verdict, axis-by-axis risk scores, and the top three reasons
                    the draft could create backlash, sponsor pressure, legal friction, or media escalation.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
            <div class="empty-card">
                <p class="section-title">Evidence Output</p>
                <h3>Retrieved context and safer wording</h3>
                <p class="empty-copy">
                    The results view will show supporting evidence from the seed corpus or your uploaded documents,
                    followed by a safer rewrite that preserves the core announcement while reducing avoidable risk.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_results(*, result: AnalysisResult, draft: str, indexed_count: int) -> None:
    verdict_style = VERDICT_STYLES[result.verdict]

    st.markdown("<div class='result-section'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <section class="verdict-banner {verdict_style['class_name']}">
            <div class="verdict-kicker">{html.escape(verdict_style['label'])}</div>
            <div class="verdict-grid">
                <div>
                    <p class="score-big">{result.overall_score}<span style="font-size: 0.42em;">/100</span></p>
                    <p class="score-caption">Overall narrative risk score</p>
                </div>
                <div>
                    <h2 style="margin: 0; color: var(--ink-inverse);">Decision signal for this draft</h2>
                    <p class="verdict-summary">{html.escape(verdict_style['summary'])}</p>
                    <p class="verdict-summary">Indexed {indexed_count} new or changed chunks during this run.</p>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    metric_cards = [
        ("Fan backlash", result.axis_scores.fan),
        ("Sponsor risk", result.axis_scores.sponsor),
        ("Legal / policy", result.axis_scores.legal_policy),
        ("Media escalation", result.axis_scores.media_escalation),
    ]
    st.markdown(
        "<div class='metric-grid'>"
        + "".join(
            (
                "<div class='metric-card'>"
                f"<div class='metric-label'>{html.escape(label)}</div>"
                f"<div class='metric-value'>{value}</div>"
                "</div>"
            )
            for label, value in metric_cards
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    insight_left, insight_right = st.columns([1.0, 1.0], gap="large")
    with insight_left:
        reasons = "".join(f"<li>{html.escape(reason)}</li>" for reason in result.top_reasons)
        st.markdown(
            f"""
            <div class="result-card">
                <p class="section-title">Top Drivers</p>
                <h3>Why this draft could create risk</h3>
                <ul class="reason-list">{reasons}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with insight_right:
        if result.likely_narratives:
            narratives_html = "<ul class='narrative-list'>" + "".join(
                f"<li>{html.escape(narrative)}</li>" for narrative in result.likely_narratives
            ) + "</ul>"
        else:
            narratives_html = "<p class='body-text' style='margin-top: 0.85rem;'>No specific narratives identified.</p>"
        st.markdown(
            f"""
            <div class="result-card">
                <p class="section-title">Narrative Pathways</p>
                <h3>Likely storylines if this goes live now</h3>
                {narratives_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    evidence_col, rewrite_col = st.columns([1.1, 0.9], gap="large")
    with evidence_col:
        st.markdown(
            """
            <div class="result-card" style="margin-top: 1rem;">
                <p class="section-title">Evidence</p>
                <h3>Retrieved supporting context</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if result.evidence:
            for item in result.evidence:
                render_evidence_card(item)
        else:
            st.markdown(
                """
                <div class="evidence-card">
                    <p class="evidence-body">No matching evidence retrieved.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with rewrite_col:
        safe_draft = html.escape(result.alternative_draft)
        original_draft = html.escape(draft.strip())
        st.markdown(
            f"""
            <div class="result-card" style="margin-top: 1rem;">
                <p class="section-title">Rewrite</p>
                <h3>Original draft</h3>
                <div class="rewrite-box">{original_draft}</div>
                <div style="height: 1rem;"></div>
                <h3>Safer wording</h3>
                <div class="rewrite-box">{safe_draft}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_evidence_card(item: RetrievedEvidence) -> None:
    meta_segments = [
        f"Similarity {item.similarity:.2f}",
    ]
    if item.summary:
        meta_segments.append(f"Summary: {item.summary}")
    if item.risk_notes:
        meta_segments.append(f"Risk notes: {item.risk_notes}")
    meta = " | ".join(meta_segments)
    st.markdown(
        f"""
        <div class="evidence-card">
            <div class="evidence-topline">
                <h3>{html.escape(item.title)}</h3>
                <div class="evidence-tag">{html.escape(format_source_type(item.source_type))}</div>
            </div>
            <div class="evidence-meta">{html.escape(meta)}</div>
            <p class="evidence-body">{html.escape(item.snippet)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_source_type(item: SourceType) -> str:
    return item.value.replace("_", " ").title()


def load_documents() -> list[Document]:
    return [Document.model_validate(item) for item in seed_documents()]


if __name__ == "__main__":
    main()
