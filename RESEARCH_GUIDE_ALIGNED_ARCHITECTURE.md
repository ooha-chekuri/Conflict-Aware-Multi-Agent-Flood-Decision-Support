# Research-Guide-Aligned Architecture

**Status: target architecture, not current implemented behavior.** This records the mini-project structure requested by the approved guide and accompanying task. It does not claim current v2/v3 already implements it.

## Scope and guardrails

- General-purpose for flood evidence in any region/type; July 2022 Godavari is an evaluation replay only.
- Decision support only. The planner returns an action level and reasons; a human retains final decision and execution authority.
- Exactly three specialists. Agents do not message one another. Each emits one common validated claim type.
- Conflict comparison, evidence scoring and action mapping are deterministic/reproducible. The hosted LLM extracts incident claims and may help explain deterministic Weather findings; it cannot override measurements, timestamps, thresholds or guideline rule matches.
- No fourth roads agent, live feeds, meaning-based LLM conflict resolution or adaptive weights in this mini project.

## Processing flow

```text
Immutable raw sources
  -> ingestion and quality checks -> versioned clean evidence + cleaning log
  -> NDMA pages -> curated rules with document/page/section/excerpt

Weather-Risk Agent       Incident-Verification Agent       Guideline-Compliance Agent
deterministic numbers    configured hosted LLM             deterministic rule matching
optional explanation    deterministic validation          provisions and citations
          \                    |                          /
           +-------------------+-------------------------+
                               |
                 canonical structured claims
                               |
             normalizer + provenance validation
                               |
          deterministic Direct/Numerical/Temporal/Geographical checks
                               |
       W = αR + βT + γG + δS + εC, with each factor logged
                               |
 Decision planner: Monitor / Advisory / Prepare / Evacuate
               OR NOT SURE + human review
                               |
          explanation + full provenance/run log
                               |
           API/dashboard + reproducible evaluation
```

Coordinate the three agents with plain Python functions unless implementation evidence later justifies orchestration tooling. This keeps the claims and data flow inspectable.

## Canonical claim contract

A strict Pydantic `Claim` (or JSON Schema equivalent) includes the required fields:

| Field | Meaning |
|---|---|
| `claim_id` | Unique derived-claim ID. |
| `agent` | One of the three specialist names. |
| `source` | Source name/identity. |
| `timestamp` | Claim/report timestamp; never substitute observation or ingestion time. |
| `location` | Place and known geographic level. |
| `value` | Structured status, number, or guideline proposition. |
| `confidence` | Agent uncertainty; not “calibrated” unless independent calibration supports it. |
| `evidence_span` | Exact source text or structured row fields supporting the claim. |
| `suggested_action` | Monitor, Advisory, Prepare, Evacuate, or null when unsupported. |

Add source/evidence IDs, source label, observed time, forecast validity, publication/availability/ingestion times, units, station, PDF page/section, model/prompt version and validation state as needed. Keep raw evidence immutable and link claims back to it.

## Three agents

### Weather-Risk Agent

Select rainfall, river-level, threshold and forecast evidence. Use Python for time/unit/location compatibility, trend calculation and warning/danger/HFL interpretation. Emit structured claims with observed/forecast type explicit. The configured LLM may produce plain-language explanations from these rule results, but cannot change values, thresholds or provenance.

### Incident-Verification Agent

This is the primary text-extraction job. For articles, official situation reports or fictional citizen reports, call one configured hosted LLM with versioned structured-output prompts to extract incident type, location, observation/report times, severity/status, exact evidence span, source identity and suggested action. Deterministically validate schema, time/timezone, source reliability metadata, duplicates, geographic relevance and evidence availability. Persist model, prompt, input, raw response, parsed claim, validation outcome and error. Calls are opt-in; demo mode must not fake an LLM result.

### Guideline-Compliance Agent

Read the available NDMA material and a versioned compact rule table. Each rule stores source filename, physical PDF page, printed page when present, section, exact excerpt, action/situation conditions and evidence IDs. Apply deterministic rule matching. Return supported, contradicted, not applicable or insufficient evidence with the comparison basis. Lexical retrieval may produce candidates; it does not itself establish relevance.

## Deterministic components

1. **Claim normalizer:** adapt agent/source outputs to the common schema and validate provenance/completeness.
2. **Conflict detector:** compare compatible claims only; return Direct, Numerical, Temporal or Geographical conflict with IDs, severity and rule explanation. Different places, units or measurement types are not direct contradictions.
3. **Evidence-weighting engine:** normalize and record `R`, `T`, `G`, `S`, and independent-source `C`; calculate `W = αR + βT + γG + δS + εC`. Store coefficient provenance/rationale. Tune only on practice data, lock/hash settings before final test. Do not select final values before that protocol.
4. **Decision planner:** map sufficient claim/guideline support to Monitor, Advisory, Prepare or Evacuate. If support is weak, tied, stale, contradictory, unavailable or outside scope, return NOT SURE, competing claims and human review. No autonomous execution.
5. **Explanation generator:** identify evidence/rules used and discounted, with reasons. LLM-written wording is constrained by deterministic outputs and persisted for audit.
6. **Provenance log:** persist inputs, claim IDs, source and time fields, model trace, conflicts, factors and coefficients, decision/abstention, explanation, guideline citations and human-review indicator.

## Data and evaluation separation

- Keep immutable raw files, cleaned evidence, guideline rules, practice data, final test, gold labels and run outputs distinct.
- Cover the guide's six scenario types. Approximate 30 total/10 practice/20 test/10–15 evidence items are Suggested; confirm against approved slides. Do not truncate v2/v3 to fit.
- Establish historical truth first, then corrupt the evidence visible to agents. Never expose gold truth/action/conflict labels to the system. Use an independent second reader and record label disagreements/adjudication.
- Run the system, B1 one-LLM, and B2 three-agent majority on identical evidence. B1 receives the same scenario evidence in one request. B2 votes on actual agent action levels; ties abstain.
- Report recommendation accuracy and macro-F1; conflict P/R/F1 overall and by type; ECE and Brier only from meaningful calibrated probabilities; provenance completeness; coverage and selective risk. Otherwise mark calibration unavailable rather than interpreting sufficiency as probability.
- Freeze practice tuning and final split before evaluation. Preserve v2/v3 as prior comparisons and write the guide-aligned run to a new version.

## Current-to-target delta

The current project has three named classes, typed evidence/output, deterministic comparisons/abstention, cited guideline retrieval, source priors, API/UI and versioned synthetic artifacts. Target behavior still requires LLM incident extraction; a canonical claim contract; all three claim streams entering conflict detection; the specified additive score; action levels; actual B1/B2; run-level provenance storage; practice-only tuning; and guide-aligned metrics/data splits. These are proposed changes, not completed work.
