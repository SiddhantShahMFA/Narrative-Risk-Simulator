from __future__ import annotations

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
from narrative_risk.models import Document, SourceType
from narrative_risk.retrieve import retrieve_evidence
from narrative_risk.seed import load_seed_documents


st.set_page_config(page_title="Narrative Risk Simulator", layout="wide")


@st.cache_resource(show_spinner=False)
def bootstrap_index() -> EmbeddingIndex:
    return EmbeddingIndex(index_path=INDEX_PATH)


@st.cache_data(show_spinner=False)
def seed_documents() -> list[dict[str, object]]:
    return [document.model_dump(mode="json") for document in load_seed_documents()]


def main() -> None:
    st.title("Narrative Risk Simulator")
    st.caption("Stress-test sports communications drafts before they go live.")

    if not has_openai_api_key():
        st.warning("Set `OPENAI_API_KEY` in your shell or `.env` file before running a full analysis.")

    left, middle, right = st.columns([1.15, 1.0, 1.1], gap="large")

    with left:
        st.subheader("Draft Input")
        draft = st.text_area(
            "Paste the draft statement",
            height=320,
            placeholder="Paste a sponsor announcement, press release, apology, or executive quote.",
        )
        st.markdown("**Upload supporting documents**")
        upload_source_type = st.selectbox(
            "Source type for TXT/MD uploads",
            options=list(SourceType),
            format_func=lambda item: item.value.replace("_", " ").title(),
        )
        title_override = st.text_input("Optional title override for TXT/MD uploads")
        uploads = st.file_uploader(
            "Upload TXT, MD, CSV, or JSON documents",
            accept_multiple_files=True,
            type=["txt", "md", "csv", "json"],
        )

        run_analysis = st.button("Run Simulation", type="primary", use_container_width=True)

    results_box = middle.container(border=True)
    evidence_box = right.container(border=True)

    if not run_analysis:
        with middle:
            st.info("Load the seed corpus, paste a draft, and run the simulator.")
        with right:
            st.info("Retrieved evidence and the safer alternative draft will appear here.")
        return

    if not draft.strip():
        st.error("A draft statement is required.")
        return
    if not has_openai_api_key():
        st.error("Set `OPENAI_API_KEY` in your shell or `.env` file before running the simulator.")
        return

    uploaded_documents = []
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

    with results_box:
        st.subheader("Risk Analysis")
        st.metric("Overall risk", f"{result.overall_score}/100", result.verdict.label)
        axis_columns = st.columns(2)
        axis_columns[0].metric("Fan backlash", result.axis_scores.fan)
        axis_columns[1].metric("Sponsor risk", result.axis_scores.sponsor)
        axis_columns[0].metric("Legal / policy", result.axis_scores.legal_policy)
        axis_columns[1].metric("Media escalation", result.axis_scores.media_escalation)
        st.markdown("**Top 3 risk reasons**")
        for reason in result.top_reasons:
            st.write(f"- {reason}")
        st.markdown("**Likely narrative pathways**")
        if result.likely_narratives:
            for narrative in result.likely_narratives:
                st.write(f"- {narrative}")
        else:
            st.write("No specific narratives identified.")
        st.caption(f"Indexed {indexed_count} new or changed chunks during this run.")

    with evidence_box:
        st.subheader("Evidence and Safer Draft")
        st.markdown("**Retrieved evidence**")
        if result.evidence:
            for item in result.evidence:
                st.markdown(
                    f"**{item.title}**  \n"
                    f"`{item.source_type.value}` · similarity `{item.similarity:.2f}`  \n"
                    f"{item.snippet}"
                )
        else:
            st.write("No matching evidence retrieved.")
        st.markdown("**Alternative draft**")
        st.text_area(
            "Safer wording",
            value=result.alternative_draft,
            height=280,
            label_visibility="collapsed",
        )


def load_documents() -> list[Document]:
    return [Document.model_validate(item) for item in seed_documents()]


if __name__ == "__main__":
    main()
