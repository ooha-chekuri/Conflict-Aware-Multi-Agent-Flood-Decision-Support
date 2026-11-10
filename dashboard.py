import json
from pathlib import Path
from datetime import datetime,timezone,date,time
import streamlit as st
from flood_support.models import Evidence
from flood_support.pipeline import run
from flood_support.synthetic_v3 import generate_evidence_v3

st.set_page_config(page_title="Flood Decision Support",layout="wide")
st.title("Conflict-Aware Multi-Agent Flood Decision Support")
st.warning("Decision support only. Outputs are not autonomous emergency instructions; a human responder retains decision authority.")
tab1,tab2,tab3,tab4=st.tabs(["Scenario analysis","Evidence explorer","Historical case study","Evaluation"])
with tab1:
    source=st.radio("Evidence set",["Synthetic scenario","Historical extracted evidence"],horizontal=True)
    if source.startswith("Synthetic"):
        examples=generate_evidence_v3(54,42); by={}
        for e in examples: by.setdefault(e.scenario_id,[]).append(e)
        sid=st.selectbox("Scenario",sorted(by)); evidence=by[sid]
    else:
        p=Path("data/processed/historical_evidence_v2.jsonl")
        if not p.exists(): p=Path("data/processed/historical_evidence.jsonl")
        if p.exists():
            evidence=[Evidence.model_validate_json(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
            # expose only one selected historical source at a time
            sources=sorted({e.source_name for e in evidence}); chosen=st.selectbox("Source document / dataset",sources); evidence=[e for e in evidence if e.source_name==chosen]
            st.caption("Corrected replay uses publication/availability only when established. The CWC 23:59:59 cutoff was an undocumented assumption and is not used as fact; MHA 18:00 is report-as-of time, not verified publication time. Unknown availability records are excluded from current-as-of support.")
            known_availability=sum(e.available_at is not None and e.available_at.tzinfo is not None for e in evidence)
            st.info(f"Selected records: {len(evidence)}; records with established availability: {known_availability}. Unknown-availability records are retained for analysis and will be marked ineligible, so the decision can explicitly abstain.")
            decision_date=st.date_input("Historical decision date",value=date(2022,7,16))
            decision_clock=st.time_input("Decision time (local IST)",value=time(23,59,59))
            cutoff=datetime.combine(decision_date,decision_clock).replace(tzinfo=__import__('datetime').timezone(__import__('datetime').timedelta(hours=5,minutes=30)))
        else: evidence=[]; st.info("Run data preparation first.")
    if evidence:
        now=cutoff if source.startswith("Historical") else max((e.available_at for e in evidence if e.available_at),default=datetime.now(timezone.utc))+__import__('datetime').timedelta(hours=1)
        result=run(evidence,now)
        d=result["decision"]; st.subheader(d["recommendation"]); st.metric("Evidence confidence indicator",d["confidence"]); st.write("Abstention:",d["abstain"],"| Human review required:",d["human_review_required"])
        c1,c2=st.columns(2)
        with c1: st.subheader("Agent contributions"); st.json(result["agents"])
        with c2: st.subheader("Conflict and decision explanation"); st.json(d)
with tab2:
    files=[Path("data/processed/pdf_pages_v2.jsonl"),Path("data/guidelines/passages_v2.jsonl")]
    files.extend([Path("data/processed/pdf_pages.jsonl"),Path("data/guidelines/passages.jsonl")])
    if any(p.exists() for p in files):
        allrows=[]
        for p in files:
            if p.exists(): allrows.extend(json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip())
        q=st.text_input("Filter source text"); rows=[r for r in allrows if q.casefold() in (r.get("text","")+r.get("source","")).casefold()] if q else allrows
        st.caption(f"{len(rows)} extracted source passages/pages")
        for r in rows[:100]:
            with st.expander(f"{r.get('source')} — page {r.get('page')}"): st.write(r.get("text"))
    else: st.info("Run prepare to extract source passages.")
with tab3:
    p=Path("data/processed/inspection_report_v2.json")
    if not p.exists(): p=Path("data/processed/inspection_report.json")
    if p.exists():
        report=json.loads(p.read_text(encoding="utf-8")); st.subheader("Input coverage and extraction audit"); st.json(report)
        st.caption("Historical reconstruction is limited to evidence available by each simulated decision time. Extracted page text is context, not a curated incident claim. No prediction is claimed.")
    else: st.info("Run prepare first.")
with tab4:
    p=Path("data/processed/evaluation_results_v3.json")
    if not p.exists(): p=Path("data/processed/evaluation_results_v2.json")
    if not p.exists(): p=Path("data/processed/evaluation_results.json")
    if p.exists():
        st.caption(f"Active evaluation artifact: {p.name}")
        st.json(json.loads(p.read_text(encoding="utf-8")))
    else: st.info("Run `python -m flood_support.cli evaluate` after generating scenarios.")
