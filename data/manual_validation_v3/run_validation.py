"""Reproduce the v3 manual workflow and guideline edge-case validation."""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from flood_support.agents.guideline import GuidelineComplianceAgent
from flood_support.models import Evidence
from flood_support.pipeline import run

OUT = Path(__file__).parent
NOW = datetime.fromisoformat("2026-11-10T12:00:00+00:00")
old_cases = [json.loads(line) for line in Path("data/manual_validation/manual_validation_cases.jsonl").read_text(encoding="utf-8").splitlines()]
agent = GuidelineComplianceAgent()
passages = agent.passages()
page = lambda n, section: next(p for p in passages if p["page"] == n and p.get("section") == section)
p64 = page(64, "3.5.2 Flood Proofing")
p66 = page(66, "3.8.5 Patient Evacuation Plan")
p89 = page(89, "8.1.3 Evacuation Plan")

def actual_pipeline(case, action=None):
    evidence = [Evidence.model_validate(x) for x in case["evidence"]]
    decision_time = datetime.fromisoformat(case.get("decision_time", NOW.isoformat()))
    response = run(evidence, decision_time, case.get("location"), action)
    decision = response["decision"]
    assessment = response["agents"]["guidelines"]["analysis"]["recommendation_check"]
    return response, {
        "recommendation": decision["recommendation"], "abstain": decision["abstain"],
        "conflicts": [{"type": c["conflict_type"], "severity": c["severity"], "evidence_ids": c["evidence_ids"]} for c in decision["conflicts"]],
        "supporting_evidence": decision["supporting_evidence"],
        "agent_claim_ids": {name: [claim["evidence_id"] for claim in output["claims"]] for name, output in response["agents"].items()},
        "guideline_result": assessment["result"],
    }

def evidence(eid, text="Flooding is reported in an affected community; warning indicators are present.", claim_type="flooding"):
    return Evidence(evidence_id=eid, scenario_id=eid, source_name="Fictional field desk", source_class="field_verified", source_label="synthetic", claim_type=claim_type, claim_text=text, location="Test Village", observed_at=NOW, reported_at=NOW, available_at=NOW, status="flooded", measurement_type="report", verified=True, completeness=1)

inputs, results = [], []
for case in old_cases[:6]:
    inputs.append(case)
    response, actual = actual_pipeline(case)
    conflicts = actual["conflicts"]
    cid = case["case_id"]
    if cid == "MV-01": passed = not conflicts and {"MV-01-E1", "MV-01-E2"}.issubset(actual["supporting_evidence"]) and not actual["abstain"]
    elif cid == "MV-02": passed = actual["abstain"] and any(c["type"] == "direct_contradiction" for c in conflicts)
    elif cid == "MV-03": passed = any(c["type"] == "temporal_staleness" for c in conflicts) and "MV-03-E1" not in actual["supporting_evidence"] and "MV-03-E2" in actual["supporting_evidence"] and not actual["abstain"]
    elif cid == "MV-04": passed = actual["abstain"] and any(c["type"] == "geographic_mismatch" for c in conflicts) and not any(c["type"] == "direct_contradiction" for c in conflicts)
    elif cid == "MV-05": passed = actual["abstain"] and any(c["type"] == "numerical_measurement" for c in conflicts)
    else: passed = actual["abstain"] and any(c["type"] == "insufficient_evidence" for c in conflicts)
    results.append({"case_id": cid, "expected_behaviour": case["expected_behaviour"], "actual_behaviour": actual, "evidence_ids": [x["evidence_id"] for x in case["evidence"]], "explanation": response["decision"]["limitations"], "pass": passed})

action = "Prepare and validate emergency evacuation plans for all organisations involved in flood-affected community evacuation before impact."
action_cases = [
    {"case_id": "MV-07", "title": "End-to-end NDMA evacuation-plan assessment", "expected_behaviour": "Assess the proposed action, cite the exact relevant provision, and retain human authority.", "proposed_action": action, "evidence": [evidence("MV-07-E1", "Flooding is reported in an affected community; warning indicators are present and organizations are preparing evacuation plans.").model_dump(mode="json")]},
    {"case_id": "MV-08", "title": "Insufficient action applicability", "expected_behaviour": "Abstain from the guideline assessment and request human review when no provision/scope can be matched.", "proposed_action": "Close the temporary access gate", "evidence": [evidence("MV-08-E1", "Flooding is reported, but local gate status is unknown.").model_dump(mode="json")]},
]
for case in action_cases:
    inputs.append(case)
    response, actual = actual_pipeline(case, case["proposed_action"])
    assessment = response["agents"]["guidelines"]["analysis"]["recommendation_check"]
    if case["case_id"] == "MV-07":
        passed = assessment["result"] == "supported" and [(p["physical_pdf_page"], p["section"]) for p in assessment["relevant_provisions"]] == [(89, "8.1.3 Evacuation Plan")] and response["decision"]["guideline_feedback"]["result"] == "supported"
    else:
        passed = assessment["result"] == "insufficient_evidence" and assessment["assessment_abstained"] and assessment["human_review_required"]
    actual["assessment"] = assessment
    results.append({"case_id": case["case_id"], "expected_behaviour": case["expected_behaviour"], "actual_behaviour": actual, "evidence_ids": [x["evidence_id"] for x in case["evidence"]], "explanation": assessment["explanation"], "pass": passed})

def assess_fixture(cid, title, expected, passage, action_text, item, query):
    case = {"case_id": cid, "title": title, "expected_behaviour": expected, "candidate_fixture": "authentic extracted NDMA passage isolated to test post-retrieval relevance; not a claim about live retrieval ranking", "proposed_action": action_text, "query": query, "evidence": [item.model_dump(mode="json")]}
    inputs.append(case)
    agent.retrieve = lambda _query, limit=5: [passage]
    assessment = agent.analyze([item], query=query, recommendation=action_text)["analysis"]["recommendation_check"]
    passed = assessment["result"] == "insufficient_evidence" and assessment["assessment_abstained"] and (not assessment["relevant_provisions"] or cid == "MV-11")
    results.append({"case_id": cid, "expected_behaviour": expected, "actual_behaviour": assessment, "evidence_ids": [item.evidence_id], "explanation": assessment["explanation"], "pass": passed})

fixture_item = evidence("MV-09-E1")
assess_fixture("MV-09", "Medical evacuation keyword is out of scope", "Retrieve page 66 as a candidate but exclude it from community evacuation-plan support.", p66, action, fixture_item, "evacuation planning")
assess_fixture("MV-10", "Flood-proofing passage is not evacuation-plan support", "Do not support an evacuation plan using unrelated flood-proofing text.", p64, action, evidence("MV-10-E1"), "flood evacuation shelter")
assess_fixture("MV-11", "Evacuation plan action lacks scope", "Abstain from assessment when action scope is incomplete.", p89, "Prepare evacuation plans", evidence("MV-11-E1"), "evacuation plan flood")

not_applicable = evidence("MV-12-E1", "Dry-weather road repair completed.", "road_repair")
inputs.append({"case_id": "MV-12", "title": "Unrelated situation", "expected_behaviour": "Classify flood guideline as not applicable.", "proposed_action": action, "evidence": [not_applicable.model_dump(mode="json")]})
assessment = agent.analyze([not_applicable], query="evacuation plan", recommendation=action)["analysis"]["recommendation_check"]
results.append({"case_id": "MV-12", "expected_behaviour": inputs[-1]["expected_behaviour"], "actual_behaviour": assessment, "evidence_ids": [not_applicable.evidence_id], "explanation": assessment["explanation"], "pass": assessment["result"] == "not_applicable"})

fixture = {"source": "synthetic_guideline_test_fixture", "page": 1, "section": "test-only prohibition", "text": "Evacuation of flood-affected communities shall not begin before official warning indicators are recorded."}
contradicted = evidence("MV-13-E1")
inputs.append({"case_id": "MV-13", "title": "Explicit prohibition test fixture", "expected_behaviour": "Classify contradicted only when a relevant passage explicitly prohibits the proposed action.", "candidate_fixture": fixture, "proposed_action": "Begin evacuation before official warning indicators are recorded", "evidence": [contradicted.model_dump(mode="json")]})
agent.retrieve = lambda query, limit=5: [fixture]
assessment = agent.analyze([contradicted], query="evacuation warning flood", recommendation=inputs[-1]["proposed_action"])["analysis"]["recommendation_check"]
results.append({"case_id": "MV-13", "expected_behaviour": inputs[-1]["expected_behaviour"], "actual_behaviour": assessment, "evidence_ids": [contradicted.evidence_id], "explanation": assessment["explanation"], "pass": assessment["result"] == "contradicted" and assessment["human_review_required"]})

(OUT / "manual_validation_cases_v3.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in inputs), encoding="utf-8")
summary = {"cases": results, "counts": {"total": len(results), "passed": sum(x["pass"] for x in results), "failed": sum(not x["pass"] for x in results)}, "limitations": ["Incident evidence is fictional.", "MV-09 and MV-10 isolate authentic extracted NDMA passages to test relevance after retrieval.", "MV-13 uses a synthetic test-only prohibition; it is not attributed to NDMA.", "Only MV-07 is an end-to-end proposed-action assessment against the actual guideline corpus."]}
(OUT / "manual_validation_results_v3.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"counts": summary["counts"], "cases": [{"id": x["case_id"], "pass": x["pass"], "result": x["actual_behaviour"].get("result", x["actual_behaviour"].get("guideline_result")), "abstain": x["actual_behaviour"].get("abstain")} for x in results]}, indent=2))
