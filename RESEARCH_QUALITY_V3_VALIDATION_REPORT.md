# Research-quality v3 validation report

**Project:** Conflict-Aware Multi-Agent Flood Decision Support System  
**Validation date:** 2026-11-10  
**Mode:** Local deterministic demo; no external LLM calls  
**Status:** v3 is the active synthetic evaluation. Earlier v2 evidence, labels, reports and metrics remain preserved.

## Changes made

- Reworked guideline assessment so lexical search returns **candidate passages**, while `relevant_provisions` contains passages classified against the proposed action. The assessment records action type, conditions and scope checks, the exact excerpt, source filename, physical PDF page, printed page when available, and section. Unresolved applicability returns `insufficient_evidence` with assessment abstention and human review. Outcomes are limited to supported, contradicted, not applicable, or insufficient evidence; this is not a compliance determination.
- Added optional `proposed_action` to `POST /analyze` and the pipeline. Existing requests without it remain valid. The guideline output is preserved in both the Guidelines Agent output and final `decision.guideline_feedback`.
- Added v3 synthetic generation and evaluation files. Agreement scenarios now use distinct source identities whenever marked independent, with a validator that rejects inconsistent independence metadata. V2 files were not regenerated or overwritten.
- Updated the README to identify v3 as active and removed its obsolete 23:59 publication/availability assumption.

## Validation results

### Guidelines and API

The original MV-07 retrieval issue is resolved: page 66, section 3.8.5, is retained as a **retrieved candidate** when lexical terms overlap, but is excluded from relevant provisions because it covers patient/medical evacuation. Page 89, section 8.1.3, is the relevant match for emergency evacuation planning. The API response retains the original PDF filename, physical page 89, section title, and full excerpt.

`POST /analyze` without `proposed_action` returned HTTP 200 and all three named agents. With the proposed action it returned a `supported` guideline assessment and preserved page 89/section 8.1.3 in final decision feedback. In both requests, the overall recommendation remained ?Escalate for human verification? and retained human authority. Eight historical records with null `available_at` were submitted at the simulated cutoff: zero were eligible for current support and the decision abstained and requested review. No availability timestamp was inferred.

The live API routes `/health`, `/openapi.json`, `/docs`, `/redoc`, `/docs/oauth2-redirect`, `/synthetic/scenarios`, `/historical/summary`, and both `/analyze` request forms returned HTTP 200. The synthetic route returned 720 v3 evidence rows. API evidence is saved in `data/manual_validation_v3/api_smoke_results_v3.json`.

### Manual scenarios

The separate v3 manual dataset passed **13/13** cases. Inputs, expected behaviour, actual outputs, explanations, evidence IDs and pass/fail labels are stored in `data/manual_validation_v3/manual_validation_cases_v3.jsonl` and `manual_validation_results_v3.json`.

| Cases | Result |
|---|---|
| MV-01 agreement from independent sources | No contradiction; support retained; human escalation |
| MV-02 direct incident contradiction | Direct conflict detected; abstain/review |
| MV-03 stale vs recent report | Staleness detected; human escalation |
| MV-04 geographic mismatch | Comparability warning; abstain/review |
| MV-05 conflicting measurements | Numerical conflict detected; abstain/review |
| MV-06 insufficient evidence | Abstain/review |
| MV-07 evacuation-plan action with flood context | Guideline assessment supported by page 89, section 8.1.3; overall decision remains human-reviewed |
| MV-08 evacuation action with insufficient context | Guideline assessment abstains as insufficient; review required; no autonomous action |
| MV-09 medical evacuation passage used for community planning | Page 66 candidate excluded as irrelevant to action scope |
| MV-10 flood-proofing passage used for evacuation planning | Page 64 candidate excluded as irrelevant |
| MV-11 incomplete evacuation action/context | Assessment abstains despite page 89 candidate |
| MV-12 unrelated dry-weather road repair | `not_applicable`; review required |
| MV-13 explicit prohibition comparison | `contradicted`; uses a clearly labelled synthetic guideline test fixture, not an NDMA provision |

### Generator and evaluation

The corrected v3 files are `data/synthetic/evidence_v3.jsonl`, `data/evaluation/labels/synthetic_gold_v3.jsonl`, and `data/processed/evaluation_results_v3.json`. Source-independence validation and separate-version tests pass. The held-out split remains scenario-family based: 200 training scenarios across five families and 160 test scenarios across four held-out families.

| Metric | Preserved v2 | Active v3 |
|---|---:|---:|
| Rule-system conflict F1 | 1.000 | 1.000 |
| Local single-agent proxy conflict F1 | 0.667 | 0.667 |
| Majority-vote conflict F1 | 0.667 | 0.667 |
| Rule-system decision accuracy | 0.969 | 1.000 |
| Rule-system coverage | 21.875% (35/160) | 25.000% (40/160) |
| Gold-abstain cases correctly abstained | 120/120 | 120/120 |
| Unnecessary abstentions in agreement family | 5/40 | 0/40 |

V3?s coverage difference comes from the corrected agreement-family source identities: the prior result abstained unnecessarily on five agreement cases because reports marked independent shared a source identity. V3 removes those five misses while keeping the same thresholds. Each held-out family contains 40 scenarios: agreement yields 40 escalations; geographic mismatch, insufficient evidence, and road-status conflict each yield 40 abstentions. These results are generated from fixed synthetic templates and author-rule labels. The v2/v3 comparison is not an independent real-world performance estimate; v3 data were regenerated and corrected.

### Dashboard

The local Streamlit server responds at `http://127.0.0.1:8501`. Four dashboard tabs were exercised through Streamlit AppTest; there were no rendering exceptions:

- **Scenario analysis:** v3 IDs appeared in the selector (54 available options); selecting `SYN3-00004` showed a geographic mismatch, abstention, evidence weights, limitations and support aggregation.
- **Historical case study:** displayed the v2 historical case evidence (152 records and 139 guideline passages). Unknown-availability records were retained and shown as ineligible; selecting the CWC bulletin yielded zero established-availability records and an abstention.
- **Evidence explorer:** the ?evacuation? filter returned 26 matching expanders. This view includes indexed historical material and was not used as a source of evaluation labels.
- **Evaluation:** displayed the active artifact `evaluation_results_v3.json`, version v3, 160 held-out scenarios, and coverage 0.25.

Browser automation was unavailable in the current environment, so no screenshots were captured. The checks used actual Streamlit AppTest widget selections and the live HTTP response; interaction result summaries are in `data/manual_validation_v3/dashboard_app_test_results.json`.

## Tests

- `python -m pytest -q`: **40 passed**, one dependency deprecation warning from Starlette?s TestClient/httpx integration.
- `python -m compileall -q flood_support dashboard.py`: passed.
- Manual validation: **13/13 passed**.
- Live API and dashboard smoke checks: passed.

## Remaining limitations and next experiments

- Guideline assessment uses conservative rules after lexical retrieval. It is not regulatory compliance review; domain experts should independently adjudicate action-condition-scope labels, especially for `not_applicable` and `contradicted` cases.
- The family holdout covers four fixed, generated families. Expand to independently authored scenario templates, varied geographies and flood mechanisms; use multiple grouped splits and keep the final test untouched.
- Evidence sufficiency is not a calibrated probability. Do not interpret confidence scores probabilistically; calibrate only after collecting independent labeled cases.
- Historical CWC publication and availability times remain unknown. Obtain archived capture/receipt metadata before making time-bounded historical claims. Current as-of handling correctly excludes unknown-availability records.
- The dataset remains synthetic or manually curated from historical documents. These results do not establish field performance, operational safety, or regulatory compliance.

Recommended next experiments: blinded guideline adjudication by flood-management experts; external review of synthetic gold labels; source-identity perturbation and duplicate-report stress tests; and prospective evaluation on timestamped, independently verified incident evidence with an untouched test set.
