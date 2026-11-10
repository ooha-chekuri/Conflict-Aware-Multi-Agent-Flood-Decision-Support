# End-to-End Functional Validation Report

**Run date:** 10 November 2026 (Asia/Calcutta)  
**Environment:** project `.venv`, deterministic local mode; no OpenAI calls  
**Result:** 8 manual cases passed; 27 tests passed; backend and dashboard responded successfully.

## Runtime and dashboard inspection

The backend is running at `http://127.0.0.1:8000`; the dashboard is running at `http://localhost:8501`.

The Streamlit root returned HTTP 200 and `/_stcore/health` returned `ok`. I inspected the four tabs in `dashboard.py`; the app is server-rendered in the browser, so the checks below describe the visible sections and data wiring rather than provide pixel screenshots:

| Dashboard tab | Visible content and v2 path | Functional observation |
|---|---|---|
| Scenario analysis | Synthetic/historical selector, scenario or source selector, historical date/time controls, agent contributions, conflict/decision output | Now retains unknown-availability historical records so the weighting panel can show `unknown` and the decision can explicitly abstain. Previously the tab filtered all such rows away before analysis; corrected in this validation. |
| Evidence explorer | Searchable PDF page text and NDMA passage excerpts | Reads v2 page/passage files when present; legacy indexes can appear alongside them, so duplicate source passages are possible. |
| Historical case study | Extraction inventory, CSV date coverage, PDF page counts, and curation limitations | Uses `inspection_report_v2.json` when present. |
| Evaluation | JSON metrics and split metadata | The current v2 file exists and identifies a family-held-out split. The legacy result is only a fallback if v2 is absent; during this run the v2 artifact was selected. |

No screenshot file was produced; the live HTTP checks and clear section descriptions are the visual evidence for this run.

## API checks

| Endpoint | Result |
|---|---|
| `GET /health` | 200; deterministic local demo mode |
| `GET /openapi.json` | 200 |
| `GET /docs` | 200 |
| `GET /synthetic/scenarios` | 200; 720 v2 evidence records |
| `GET /historical/summary` | 200; reports 152 historical records and 139 guideline passages |
| `POST /analyze` direct contradiction | 200; returned weather, incident, and guideline agent outputs; detected `direct_contradiction`; abstained |
| `POST /analyze` insufficient evidence | 200; detected `insufficient_evidence`; abstained |
| `POST /analyze` historical unknown availability | 200; `available_at=null`, status `unknown`, ineligible, abstained |

Detailed API responses are saved separately in [api_smoke_results.json](/C:/Users/oohac/OneDrive/Documents/Conflict-Aware%20Multi-Agent%20Flood%20Decision%20Support/data/manual_validation/api_smoke_results.json).

## Agent and data-flow checks

- **Weather Risk Agent:** manual numerical case MV-05 was emitted as two claims with source provenance and reached the conflict detector, which returned a high-severity numeric conflict. I also sent the v2 historical forecast records through the agent: it identified nine forecasts separately from observations and retained provenance. A focused test caught simultaneous readings being incorrectly summarized as a trend; the agent now reports `insufficient_series` unless observations have distinct times.
- **Incident Verification Agent:** cases MV-01 through MV-04 and MV-06 show incident claims and their evidence IDs in the pipeline output. Direct contradictions, stale records, location mismatch, and sparse evidence changed downstream conflicts and decisions. Existing integration tests also verify that removing an emitted claim changes downstream conflict output and that duplicated evidence IDs are counted once.
- **Guideline Compliance Agent:** produced structured guideline claims, candidate findings, uncertainties, and citations. Manual case MV-07 retrieved the supplied NDMA PDF’s physical page 89, section 8.1.3, *Evacuation Plan*, for the evacuation-plan query. MV-08 returned `insufficient_evidence`. These are retrieval-level support labels, not legal or regulatory compliance determinations.
- **Downstream decisions:** agent claims feed `analyze`; guideline feedback accompanies the final decision. A clear functional defect was found: guideline `insufficient_evidence` was blocking even a generic referral for human verification. The decision now preserves the guideline uncertainty and human-review requirement without abstaining solely for that reason; explicit guideline contradiction still blocks. This does not change source weights, cutoffs, or gold labels.

## Manual validation cases

The separate inputs and results are in [manual_validation_cases.jsonl](/C:/Users/oohac/OneDrive/Documents/Conflict-Aware%20Multi-Agent%20Flood%20Decision%20Support/data/manual_validation/manual_validation_cases.jsonl) and [manual_validation_results.json](/C:/Users/oohac/OneDrive/Documents/Conflict-Aware%20Multi-Agent%20Flood%20Decision%20Support/data/manual_validation/manual_validation_results.json). All inputs are fictional and labeled `synthetic`.

| ID | Case | Actual behavior | Result |
|---|---|---|---|
| MV-01 | Two independent reports agree | No conflict; both evidence IDs support “Escalate for human verification”; not abstained | Pass |
| MV-02 | Reports disagree on flooding | High-severity direct contradiction; abstained | Pass |
| MV-03 | 30-hour-old report plus recent report | Staleness warning; old ID excluded from support, recent ID retained; human-verification referral | Pass |
| MV-04 | Same event, different locations | Geographic mismatch only (informational); no false direct contradiction; abstained | Pass |
| MV-05 | Same-gauge rainfall values disagree | High-severity numerical conflict; abstained | Pass |
| MV-06 | Sparse, unverified incident claim | Insufficient-evidence conflict; no supporting evidence; abstained | Pass |
| MV-07 | NDMA evacuation-plan provision | Candidate support retrieved from page 89, section 8.1.3, with source/page citation | Pass |
| MV-08 | Proposed access-gate action lacks a matching provision | `insufficient_evidence`; no matching citation invented | Pass |

All eight case criteria passed. MV-07 and MV-08 directly invoke the guideline agent because the current `POST /analyze` request schema does not accept a caller-proposed action. The full pipeline’s recommendation is generated internally.

## v2 coverage and abstention analysis

The stored test set has 160 scenarios: 40 per held-out family. Coverage is 35/160 = **21.875%** (21.9%); therefore 125/160 abstain.

| Held-out family | Escalation / non-abstain | Abstentions | Primary abstention reason |
|---|---:|---:|---|
| agreement | 35 | 5 | Support did not reach the configured threshold after same-source reports were deduplicated |
| geo_mismatch | 0 | 40 | Geographic comparability warning; do not combine the locations |
| road_status_conflict | 0 | 40 | High-severity status conflict |
| insufficient | 0 | 40 | Insufficient evidence |
| **Total** | **35** | **125** | |

The five agreement cases are inconsistent with their gold expectation of independent corroboration: their two generated records have the **same source name** despite `independent_source=true`. The decision engine deduplicates their contribution by source name, so they fall below the existing support threshold. These are five abstentions that are unnecessary relative to the gold label, but the input records do not actually establish two independent sources. This is a generator/label consistency limitation, not a reason to loosen thresholds. The other 120 abstentions are justified by the evidence or conflict state.

Per-family counts and the five affected scenario IDs are saved in [abstention_breakdown_v2.json](/C:/Users/oohac/OneDrive/Documents/Conflict-Aware%20Multi-Agent%20Flood%20Decision%20Support/data/manual_validation/abstention_breakdown_v2.json).

## Historical availability check

The v2 dataset has `available_at=null` and `published_at=null` for the supplied historical records whose publication/receipt time is unknown. CWC forecast validity remains separately recorded (for example, `2022-07-16T21:00:00+05:30`); it does not establish when the forecast became available. MHA’s 18:00 value remains report-as-of time, not publication time. An API replay at the requested historical cutoff returned `availability=unknown`, `eligible=false`, and abstention. No old 23:59 assumption was restored.

## Fixes made during this validation

1. `flood_support/agents/weather.py`: simultaneous values from multiple sources no longer create a rising/falling trend. Added a focused regression test.
2. `dashboard.py`: unknown-availability historical evidence is retained through analysis and shown with an availability count, allowing the decision panel to display its abstention instead of showing an empty result.
3. `flood_support/decision.py`: guideline uncertainty no longer blocks a generic human-verification referral; guideline contradiction still blocks. The output retains the guideline limitation. Added tests for both branches.

No evaluation thresholds, prior labels, old evaluation results, or source files were changed. Manual outputs are stored under `data/manual_validation/`.

## Test results and limitations

- Original suite: 23 tests; all pass.
- Added focused validation tests: 4; all pass.
- Total: **27 passed**.
- API and dashboard smoke checks passed. Both services were started in the current `.venv`.

The dashboard was checked through its source-defined tabs and live root/health endpoints; automated browser interaction and screenshots were not available in this run. Guideline retrieval remains lexical. Synthetic test cases and labels are not independently expert-adjudicated. The 21.9% coverage is specific to the fixed synthetic held-out families and is not a real-world operating characteristic.
