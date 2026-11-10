# Research Guide Alignment Implementation Plan

**Status:** Proposed and awaiting approval. No application implementation has begun.

## Preservation rules

- Work only in the existing project.
- Do not edit or remove `data/raw/` files.
- Keep v2/v3 inputs, labels, metrics and reports immutable.
- Put any new cleaned evidence, rule table, practice/test set, model traces and metrics under a new versioned location (proposed `v4_guide_aligned/`; confirm before creation).
- Keep API keys in environment variables; use public or fictional incident text for hosted calls and redact personal information.
- Never tune on final test data or present prototype scores as real-world safety/compliance evidence.

## Phases and gates

| Phase | Work | Exit evidence / gate |
|---|---|---|
| 0. Protocol confirmation | Confirm action-level semantics and NOT SURE behavior; confirm whether Suggested 30 scenarios/10 practice/20 test aligns with slides; specify second-reader labels and final-test handling. Define coefficient/threshold tuning protocol without choosing unvalidated values. | Reviewed protocol; assumptions visible and no test peeking. |
| 1. Claim contract and lineage | Define canonical Pydantic `Claim`; add adapters from existing `Evidence`; require agent, source, timestamp semantics, location, confidence, evidence span and suggested action. Add integration test proving Weather, Incident and Guideline claims all reach deterministic conflict checks. | Schema/provenance tests pass; existing API and v2/v3 artifacts remain usable. **Recommended first implementation task.** |
| 2. Data quality and replay inputs | Create row-level rainfall diagnostics and cleaned derivatives. Flag missing, stuck-sensor and high/impossible candidates for review; preserve row IDs and exclusion reasons. Reconcile actual CSV station/date coverage with guide estimates. Record source observation, report, publication/availability and ingestion times separately. Remove the unsafe legacy 23:59 path from future active-data generation. | Cleaning/replay report and tests; no unsupported “usable” data or availability claims. |
| 3. Three specialist agents | Weather emits deterministic numerical/threshold claims with optional constrained explanation. Incident performs hosted structured extraction with deterministic validation and saved prompt/model/input/output. Guideline matches curated NDMA rules with page/section/excerpt. Provide honest API-disabled deterministic demo mode. | Valid structured output/provenance; tests for malformed model output, dates, duplicates and place validation. |
| 4. Conflict, score and planner | Route all claims through the normalizer. Align Direct/Numerical/Temporal/Geographical rules. Implement/log `W=αR+βT+γG+δS+εC`. Add Monitor/Advisory/Prepare/Evacuate plus NOT SURE/human review. Keep official thresholds/numeric checks deterministic. | Tests for comparability, all conflict types, factor arithmetic, ties, unknown availability and review outcomes. |
| 5. Practice/test data and labels | After Phase 0, build six scenario types from documented historical truth, then perturb only agent-visible evidence. Keep labels hidden from input. Have a second reader label independently, reconcile, freeze and hash the test split. | Data card, provenance, adjudication log, split manifest and final-test checksum. |
| 6. Baselines | B1: one configured hosted LLM reads identical scenario evidence; opt-in, strict output, complete trace. B2: three real specialist votes on action level with documented ties. | Input parity tests; versioned prompts/model IDs and saved exact requests/responses/errors. |
| 7. Tuning and evaluation | Tune coefficients/thresholds on practice only, lock configuration, run final test once. Report recommendation accuracy/macro-F1; conflict P/R/F1 by type; ECE/Brier only when probabilities are valid; provenance, coverage and selective risk. Leave old results unchanged. | Reproducible evaluation bundle with labels, split/config hashes, limitations and error review. |
| 8. UI and final verification | Show action level, claim comparison, conflict/factor reasons, guideline citations, provenance and abstention in API/dashboard. Preserve prior routes where possible. Verify deterministic demo and separately configured optional LLM workflow. | End-to-end test, dashboard walkthrough and new guide-aligned report. |

## Existing components to reuse/adapt

| Existing component | Reuse | Adaptation |
|---|---|---|
| `models.py` | Pydantic and time/source fields | Add canonical Claim and Evidence adapters. |
| `agents/weather.py` | Deterministic trend/threshold work | Emit claims and bounded explanations. |
| `agents/incident.py` | Duplicate/location checks | Add primary LLM extraction and deterministic validation. |
| `agents/guideline.py` | Page-cited retrieval and conservative tests | Add curated rule records; feed claims through common pipeline. |
| `conflicts.py` | Deterministic compatible-value checks | Align four names/semantics and paired temporal logic. |
| `decision.py`, `config/source_reliability.json` | Availability checks, priors and review logic | Replace product score with weighted sum; action-level planner and factor ledger. |
| `llm.py` | Env-configured OpenAI Responses call | Generalize for incident/B1, version prompts and persist traces. |
| `evaluation_v2.py`, `evaluation_v3.py` | Prior artifacts/split experience | Leave unchanged; add new evaluator with actual B1/B2 and guide metrics. |
| `synthetic_v3.py`, `gold_v3.py` | Source identity validation/separate labels | Leave unchanged; create new practice/test artifacts only after protocol agreement. |
| `ingest.py` | Inventory, hashes, PDF page extraction, v2 null availability | Add reviewed cleaning outputs and prevent unsafe legacy regeneration. |
| `data_access.py`, `api.py`, `dashboard.py` | Existing service and UI | Add run-level provenance persistence and action-level display after core tests. |

## Explicitly out of scope

No fourth agent, live-feed deployment, new hazards, semantic LLM conflict detector, adaptive/learned weights, automatic replanning, human-subject study, route optimization, B3/B4 baselines or major-project features marked `[Later]` in the guide.

## Approval requested

Approve or revise **Phase 1: canonical claim contract, backward-compatible Evidence adapters, and an integration test proving that all three agent claim streams reach deterministic conflict detection**. Work pauses here until approval.
