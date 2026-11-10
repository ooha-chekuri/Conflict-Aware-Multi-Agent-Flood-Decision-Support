# Conflict-Aware Multi-Agent Flood Decision Support System

An explainable, deterministic-first research prototype for comparing flood evidence and producing reviewable decision support. It is **not** a flood prediction model or an autonomous emergency instruction system. A human responder retains authority.

## What the supplied files contain

See `data/processed/inspection_report.json` after running preparation. Initial inspection found 11 supplied files: three CSVs and eight PDFs. `PDF` is the MHA 16 July 2022 situation report; `PDF (1)` is its 15 July counterpart. `flood.pdf` is the NDMA *National Disaster Management Guidelines: Management of Floods*. The CWC bulletin and situation report, 2022 appraisal, and two NRSC maps are included. Originals are copied byte-for-byte into `data/raw/` and are never edited.

The IMD statewise/districtwise CSVs have records dated through 2026-11-05 and their supplied snapshots do not provide records for 2022-07-16. The telemetry file includes hourly Andhra Pradesh CWC records from 2021-2025, including 91 rainfall records timestamped on 2022-07-16. The rainfall telemetry is rainfall, not river-level data. The CWC bulletin's 16 July station table is manually transcribed into separate observed and forecast records with warning, danger, and previous-HFL levels; the MHA report contributes its official CWC above-danger offsets and Andhra Pradesh impact-table values. These hand-curated records cite PDF pages and are flagged for independent review. CWC report/bulletin publication times are not printed, so publication and availability timestamps remain unknown; as-of analysis excludes these records and may abstain. Satellite maps are visual evidence and map text extraction does not turn their mapped inundation into georeferenced village observations.

## Quick start

Python 3.11+ recommended. From this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m flood_support.cli prepare-v2
python -m flood_support.cli generate-v3 --count 360 --seed 2026
python -m flood_support.cli evaluate-v3
python -m pytest -q
python -m uvicorn flood_support.api:app --reload
python -m streamlit run dashboard.py
```

The deterministic pipeline and dashboard work without an API key. `OPENAI_API_KEY` and `OPENAI_MODEL` configure the optional OpenAI Responses API single-agent evaluation baseline; it is disabled by default. Run `python -m flood_support.cli evaluate --llm-baseline` only when you want the external, potentially billable comparison. The core conflict and numeric evidence checks never defer to an LLM.

For the family-held-out evaluation, use the versioned workflow. It writes new files and leaves the original synthetic labels and metrics untouched:

```powershell
python -m flood_support.cli generate-v3 --count 360 --seed 2026
python -m flood_support.cli evaluate-v3
```

The active v3 evaluation holds out four complete scenario families (200 training scenarios across five families; 160 test scenarios across four families). Its labels come from a separate, explicit author rulebook and are still synthetic rather than independently expert-adjudicated. `prepare-v2` writes `historical_evidence_v2.jsonl`, `pdf_pages_v2.jsonl`, `passages_v2.jsonl`, and `inspection_report_v2.json` with unknown publication/availability timestamps left null. It leaves the old derived files and SQLite database untouched. The dashboard uses v3 evaluation and synthetic scenarios when present, with v2 historical evidence. V2 evidence, labels, metrics and historical artifacts remain preserved.

### Evaluation record

The previous saved evaluation is preserved unchanged: its conflict F1 was 1.00 for the system, 0.00 for the local trivial proxy, and 0.791 for majority vote; decision accuracy was 0.792, 0.542, and 1.00 respectively. The old split mixed every scenario family across train and test, and its majority result followed the generator patterns.

The reproducible v3 run (`--count 360 --seed 2026`) holds out whole families. Its synthetic test metrics are: conflict F1 1.00 for the rule system, 0.667 for the independent local single-agent heuristic, and 0.667 for majority vote; multi-class conflict-type accuracy 1.00; decision accuracy 1.00 for the system, 0.50 for each baseline; system coverage 0.25 and correct abstention on 1.00 of gold-abstain cases. The test has 160 cases, including 120 expected abstentions and 40 expected escalations. The high template-level scores are not real-world validation: the labels are explicit author rules, scenarios remain synthetic, and only four fixed families are held out. Confidence calibration error is intentionally null because the confidence output is an evidence sufficiency indicator, not a calibrated probability.

## Architecture

- Weather Risk Agent: rainfall/river observations and forecasts, with observed/forecast type explicitly retained.
- Incident Verification Agent: status reports, duplication, staleness, location mismatches, and corroboration.
- Guideline Compliance Agent: local guideline passage retrieval with PDF page and section provenance. Retrieval is lexical and conservative; unclear applicability is reported as insufficient evidence.
- Rule-based conflict engine: compares compatible measurements and statuses with configurable temporal/geographic tolerances.
- Evidence weighting and decision engine: transparent components, conflict penalties, support/counterevidence, confidence, and abstention.
- SQLite persistence, FastAPI API, and Streamlit dashboard.

`data/raw`, `data/processed`, `data/synthetic`, `data/evaluation/labels`, and `data/guidelines` remain distinct. Synthetic labels are stored separately from input evidence. The evaluation harness uses a seeded train/test partition and reports deterministic system, majority vote, and single-agent baseline scores. Its default local baseline is a reproducible proxy, **not** a claim of equivalence to an external LLM. With `--llm-baseline`, it sends only held-out fictional scenarios to the configured model. The OpenAI client uses the [Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create) and structured JSON output; model output cannot override the deterministic conflict engine or thresholds.

## Data preparation and use

`prepare-v2` inventories the files, hashes them, extracts PDF text per page, extracts an auditable guideline passage index, validates CSV schemas/date coverage, and writes versioned historical files without replacing prior derived files or the SQLite database. It does not silently interpret map imagery or infer unreported river levels. All PDF-derived passages include source filename and physical page number. Historical records with unknown availability remain out of as-of recommendations; this limitation is shown in the dashboard and API summary.

Synthetic generation creates configurable scenario families (consistent, direct contradiction, numerical, stale, geographic mismatch, evacuation/road status, insufficient evidence, corroborated, and varied flood settings). Each evidence row says `synthetic`, has evidence/scenario IDs and timestamps/location; expected conflict and gold outcome are held in a separate labels file.

## API

- `GET /health`
- `POST /analyze` with `{ "evidence": [...] }`; optional `proposed_action` enables an evidence-linked guideline assessment.
- `GET /synthetic/scenarios`
- `GET /historical/summary`

Every response is decision support and retains evidence IDs, source labels, timestamps and explanation strings.

## Research limitations

This repository is a prototype, not validated operational software. Reliability weights are configurable documented assumptions, not empirical certification. Historical reconstruction is bounded by supplied document publication times and extracted content. Guideline search returns candidate passages, not a legal/compliance determination. The evaluation gold labels are synthetic author-defined labels, not field-validated outcomes. Do not use for live emergency decisions without independent human verification.
