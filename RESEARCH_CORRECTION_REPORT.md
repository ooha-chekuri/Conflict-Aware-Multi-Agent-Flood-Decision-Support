# Research Correction Report

## Scope and preservation

This incrementally corrects the existing project. It does not replace the application or edit the supplied raw files. The previous `historical_evidence.jsonl`, `synthetic_gold.jsonl`, and `evaluation_results.json` remain in place; the updated workflow writes versioned v2 outputs.

## Corrections implemented

- **Agent workflow:** the weather and incident agents emit typed claims, findings, uncertainty notes, and provenance. The pipeline deduplicates claims by evidence ID and sends their structured claims into conflict analysis and decision scoring. Guideline retrieval now emits source-cited claim records and a separate, conservative recommendation assessment. Raw evidence remains in the response. See `flood_support/pipeline.py` and `flood_support/agents/`.
- **Evidence scoring and abstention:** source-class priors, completeness, availability, age/validity, and explicit geographic matching now affect eligibility and support. Same-source repeats count once; corroboration only receives a configurable bonus when distinct sources are explicitly marked independent. Unavailable, timezone-ambiguous, future, stale, incomplete, unverified-report, geographically uncertain, or high-conflict evidence cannot silently support a current recommendation. Confidence is labelled an uncalibrated evidence-sufficiency indicator. See `flood_support/decision.py`, `flood_support/temporal.py`, `flood_support/geography.py`, and `config/source_reliability.json`.
- **Conflict handling:** comparisons require evidence to have been available by the decision time and require compatible locations, measurement types, units, and timestamps. Geographic mismatch is a comparability warning, not a direct contradiction. Sparse claims can be explicitly marked insufficient. See `flood_support/conflicts.py`.
- **Historical replay:** `prepare-v2` records observation, report-as-of, forecast-validity, and ingestion times separately. Unknown publication and availability times remain null. The CWC 23:59:59 cutoff is treated as a legacy assumption only; MHA 18:00 is stored as report-as-of time, not publication time. The versioned preparation command writes `historical_evidence_v2.jsonl`, `pdf_pages_v2.jsonl`, `passages_v2.jsonl`, and `inspection_report_v2.json` without replacing prior processed data or the SQLite database.
- **Guidelines:** candidate passages retain document name, physical PDF page, section, and printed page when extractable. The assessment distinguishes `supported`, `contradicted`, `not_applicable`, and `insufficient_evidence`; lexical matching only identifies a candidate textual support signal and is not a compliance determination. Uncertain applicability remains for human review. No new official rule or threshold is inferred.
- **Evaluation:** `synthetic_v2.py` generates varied fictional evidence; `gold_v2.py` assigns labels separately under a declared rulebook; `evaluation_v2.py` holds out complete families. It reports binary and multi-class conflict results, decision outcomes, baselines, abstention, provenance completeness, and leaves calibration error null because confidence is not a probability. OpenAI is not called. Old results are preserved.
- **Application:** dashboard and API prefer v2 historical, synthetic, and evaluation artifacts when available. FastAPI and Streamlit interfaces remain.

## Updated v2 evaluation

Reproduced with seed 2026, 360 scenarios, 720 evidence rows, 200 training scenarios across five families, and 160 test scenarios across four held-out families (`agreement`, `geo_mismatch`, `insufficient`, and `road_status_conflict`).

| Metric | Rule system | Local single-agent heuristic | Majority vote |
|---|---:|---:|---:|
| Binary conflict precision | 1.000 | 1.000 | 1.000 |
| Binary conflict recall | 1.000 | 0.500 | 0.500 |
| Binary conflict F1 | 1.000 | 0.667 | 0.667 |
| Decision-outcome accuracy | 0.969 | 0.500 | 0.500 |

Multi-class conflict-type accuracy is 1.000 on the held-out synthetic templates. System coverage is 0.219; all gold-abstain cases were abstained on, while 5 of 40 expected escalation cases were conservatively abstained on. Provenance completeness is 1.000 under the v2 structural definition. Calibration error is null. Full confusion matrices and per-class details are in `data/processed/evaluation_results_v2.json`.

For comparison, the preserved prior evaluation reports conflict F1 values of 1.000 for the system, 0.000 for the local trivial proxy, and 0.791 for majority vote; decision accuracy values are 0.792, 0.542, and 1.000. That earlier split mixed every scenario family across train and test. The new metrics are still synthetic and author-labelled; high template scores do not establish operational or real-world validity.

## Validation performed

- `python -m pytest -q`: **23 passed**.
- `python -m compileall -q flood_support dashboard.py`: passed.
- FastAPI `/health`: HTTP 200, deterministic local demo mode.
- Streamlit health endpoint: `ok` after launching the dashboard.
- Historical v2 evidence was parsed and sent through the same agent pipeline used for synthetic evidence. With publication availability unknown, the decision correctly abstained.
- A temporary-input test verifies `prepare-v2` leaves an existing legacy historical file unchanged.

## Remaining research limitations

- The historical source files do not establish publication/availability times for telemetry or the CWC PDFs. Consequently, those records are excluded from time-specific operational support in v2; historical decision reconstruction at finer times remains unavailable without source release/receipt times. The system must not restore 23:59 as fact.
- NDMA retrieval is deterministic lexical retrieval plus rule-based topical comparison, not expert legal interpretation. Printed page numbers remain null where extraction did not clearly expose one; physical PDF pages are retained.
- Gold labels are generated by a separate, documented author rulebook but have not been independently adjudicated. Held-out families reduce template leakage but the scenarios are still artificial, and baseline rules operate on the same constrained evidence schema.
- Reliability and decision thresholds are documented starting assumptions, not empirically calibrated. Confidence calibration is not claimed.
- No live hydrologic prediction, satellite polygon extraction, or field validation is performed. A human responder retains authority.

## Commands

From the project root in PowerShell, with the existing `.venv` installed:

```powershell
.\.venv\Scripts\python.exe -m flood_support.cli prepare-v2
.\.venv\Scripts\python.exe -m flood_support.cli generate-v2 --count 360 --seed 2026
.\.venv\Scripts\python.exe -m flood_support.cli evaluate-v2
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn flood_support.api:app --reload
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

`prepare-v2` and the v2 generation/evaluation commands do not overwrite the old historical data, gold labels, or evaluation result. No API key is needed for this deterministic workflow.
