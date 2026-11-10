from datetime import datetime, timezone

from flood_support.agents.guideline import GuidelineComplianceAgent
from flood_support.models import Evidence

P89={"source":"ndma_guidelines_management_of_floods.pdf","page":89,"section":"8.1.3 Evacuation Plan","printed_page":57,"text":"Preparing plans of all organisations involved in emergency evacuation for flood-affected communities; validating plans and testing the established procedures."}
P66={"source":"ndma_guidelines_management_of_floods.pdf","page":66,"section":"3.8.5 Patient Evacuation Plan","printed_page":34,"text":"Paramedical staff must be trained during evacuation. Heli-ambulances need to be deployed to aid evacuation of flood casualties collected at high points."}
ACTION="Prepare and validate emergency evacuation plans for all organisations serving flood-affected communities before impact."

def flood_evidence(**updates):
    data=dict(evidence_id="g1",source_name="field desk",source_class="field_verified",source_label="synthetic",claim_type="flooding",claim_text="Flooding is reported and the district is assessing evacuation planning.",location="Test Village",observed_at=datetime(2026,1,1,tzinfo=timezone.utc),available_at=datetime(2026,1,1,tzinfo=timezone.utc),status="flooded",measurement_type="report",verified=True,completeness=1)
    data.update(updates)
    return Evidence(**data)

def test_medical_evacuation_keyword_is_not_relevant_to_community_plan(monkeypatch):
    agent=GuidelineComplianceAgent()
    monkeypatch.setattr(agent,"retrieve",lambda query,limit=5:[P66])
    result=agent.analyze([flood_evidence()],query="evacuation plan emergency flood",recommendation=ACTION)
    check=result["analysis"]["recommendation_check"]
    assert check["result"]=="insufficient_evidence"
    assert check["assessment_abstained"] and check["human_review_required"]
    assert check["retrieved_candidate_citations"][0]["physical_pdf_page"]==66
    assert check["relevant_provisions"]==[]

def test_irrelevant_flood_proofing_passage_is_not_matched_by_shared_keywords(monkeypatch):
    agent=GuidelineComplianceAgent()
    passage={"source":"ndma.pdf","page":64,"section":"3.5.2 Flood Proofing","text":"Flood proofing provides raised shelter platforms; this measure does not involve evacuation."}
    monkeypatch.setattr(agent,"retrieve",lambda query,limit=5:[passage])
    check=agent.analyze([flood_evidence()],query="flood evacuation shelter",recommendation=ACTION)["analysis"]["recommendation_check"]
    assert check["result"]=="insufficient_evidence"
    assert check["relevant_provisions"]==[]
    assert check["retrieved_candidate_citations"][0]["section"]=="3.5.2 Flood Proofing"

def test_matching_evacuation_plan_provision_is_separated_from_page_66_candidate(monkeypatch):
    agent=GuidelineComplianceAgent()
    monkeypatch.setattr(agent,"retrieve",lambda query,limit=5:[P66,P89])
    check=agent.analyze([flood_evidence()],query="emergency evacuation planning flood",recommendation=ACTION)["analysis"]["recommendation_check"]
    assert check["result"]=="supported"
    assert len(check["retrieved_candidate_citations"])==2
    assert [(p["physical_pdf_page"],p["section"]) for p in check["relevant_provisions"]]==[(89,"8.1.3 Evacuation Plan")]
    assert check["relevant_provisions"][0]["source"]=="ndma_guidelines_management_of_floods.pdf"
    assert check["relevant_provisions"][0]["excerpt"]==P89["text"]

def test_supplied_ndma_pages_66_and_89_have_distinct_action_scopes(monkeypatch):
    agent=GuidelineComplianceAgent()
    indexed=agent.passages()
    medical=next(p for p in indexed if p["page"]==66 and p.get("section")=="3.8.5 Patient Evacuation Plan")
    planning=next(p for p in indexed if p["page"]==89 and p.get("section")=="8.1.3 Evacuation Plan")
    assert "casualties" in medical["text"].casefold()
    assert "organisations involved in the emergency evacuation" in planning["text"].casefold()
    monkeypatch.setattr(agent,"retrieve",lambda query,limit=5:[medical,planning])
    check=agent.analyze([flood_evidence()],query="evacuation planning",recommendation=ACTION)["analysis"]["recommendation_check"]
    assert [p["physical_pdf_page"] for p in check["retrieved_candidate_citations"]]==[66,89]
    assert [p["physical_pdf_page"] for p in check["relevant_provisions"]]==[89]

def test_missing_action_scope_or_conditions_abstains_from_guideline_assessment(monkeypatch):
    agent=GuidelineComplianceAgent()
    monkeypatch.setattr(agent,"retrieve",lambda query,limit=5:[P89])
    check=agent.analyze([flood_evidence()],query="evacuation plan flood",recommendation="Prepare evacuation plans")["analysis"]["recommendation_check"]
    assert check["result"]=="insufficient_evidence"
    assert check["assessment_abstained"] and check["human_review_required"]
    assert check["relevant_provisions"]==[agent._citation(P89)]

def test_explicit_prohibition_can_contradict_proposed_action(monkeypatch):
    agent=GuidelineComplianceAgent()
    passage={"source":"ndma.pdf","page":89,"section":"8.1.3 Evacuation Plan","text":"Evacuation of flood-affected communities shall not begin before official warning indicators are recorded."}
    monkeypatch.setattr(agent,"retrieve",lambda query,limit=5:[passage])
    check=agent.analyze([flood_evidence()],query="evacuation warning flood",recommendation="Begin evacuation before official warning indicators are recorded")["analysis"]["recommendation_check"]
    assert check["result"]=="contradicted"
    assert check["human_review_required"]

def test_unrelated_situation_is_not_applicable(monkeypatch):
    agent=GuidelineComplianceAgent()
    monkeypatch.setattr(agent,"retrieve",lambda query,limit=5:[P89])
    item=flood_evidence(claim_type="road_repair",claim_text="Road repair completed in dry weather.")
    check=agent.analyze([item],query="evacuation plan",recommendation=ACTION)["analysis"]["recommendation_check"]
    assert check["result"]=="not_applicable"
