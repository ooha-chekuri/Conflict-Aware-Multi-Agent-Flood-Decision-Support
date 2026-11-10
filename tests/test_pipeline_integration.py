from datetime import datetime, timezone

from flood_support.models import Evidence
from flood_support.pipeline import collect_unique_agent_claims, run

NOW=datetime(2025,1,1,12,tzinfo=timezone.utc)

def rainfall(eid,value):
    return Evidence(
        evidence_id=eid,source_name=f"source-{eid}",source_class="synthetic",
        source_label="synthetic",claim_type="rainfall",claim_text=f"{value} mm/hour",
        location="Gauge A",observed_at=NOW,reported_at=NOW,available_at=NOW,
        value=value,unit="mm/hour",measurement_type="observation",
        metadata={"station":"Gauge A"})

def test_weather_claim_output_changes_downstream_conflicts(monkeypatch):
    evidence=[rainfall("r1",80),rainfall("r2",25)]
    full=run(evidence,NOW)
    assert any(c["conflict_type"]=="numerical_measurement" for c in full["decision"]["conflicts"])

    def omit_second(self, raw):
        return {"claims":[raw[0].model_dump(mode="json")],"findings":[],"uncertainties":["test omission"],"provenance":[]}
    monkeypatch.setattr("flood_support.pipeline.WeatherRiskAgent.analyze",omit_second)
    reduced=run(evidence,NOW)
    assert not any(c["conflict_type"]=="numerical_measurement" for c in reduced["decision"]["conflicts"])
    assert len(reduced["raw_evidence"])==2

def test_repeated_agent_reference_to_same_source_is_counted_once():
    claim=rainfall("r1",80).model_dump(mode="json")
    outputs=({"claims":[claim]},{"claims":[claim]})
    unique=collect_unique_agent_claims(*outputs)
    assert len(unique)==1 and unique[0].evidence_id=="r1"

def test_agent_outputs_retain_provenance_and_flow_through_full_pipeline(monkeypatch):
    evidence=[rainfall("r1",80)]
    result=run(evidence,NOW,location="Gauge A")
    weather=result["agents"]["weather"]
    assert weather["claims"][0]["evidence_id"]=="r1"
    assert weather["provenance"][0]["source_name"]=="source-r1"
    assert result["decision"]["evidence_weights"][0]["evidence_id"]=="r1"

def test_unknown_historical_availability_is_retained_but_cannot_support_decision():
    item=rainfall("unknown-availability",80).model_copy(update={"available_at":None,"source_label":"historical"})
    result=run([item],NOW)
    assert result["raw_evidence"][0]["evidence_id"]=="unknown-availability"
    assert result["decision"]["abstain"]
    weight=result["decision"]["evidence_weights"][0]
    assert weight["availability"]=="unknown"
    assert not weight["eligible_for_current_support"]

def test_proposed_action_reaches_guideline_assessment_and_final_decision():
    evidence=[Evidence(evidence_id="flood",source_name="District Desk",source_class="field_verified",source_label="synthetic",claim_type="flooding",claim_text="Flood-affected community is preparing an emergency evacuation plan.",location="Test Village",observed_at=NOW,reported_at=NOW,available_at=NOW,status="flooded",measurement_type="report",verified=True,completeness=1)]
    action="Prepare and validate emergency evacuation plans for all organisations serving flood-affected communities before impact."
    result=run(evidence,NOW,location="Test Village",proposed_action=action)
    assessment=result["agents"]["guidelines"]["analysis"]["recommendation_check"]
    assert result["proposed_action"]==action
    assert assessment["proposed_recommendation"]==action
    assert assessment["result"]=="supported"
    assert [(p["physical_pdf_page"],p["section"]) for p in assessment["relevant_provisions"]]==[(89,"8.1.3 Evacuation Plan")]
    assert assessment["result"]==result["decision"]["guideline_feedback"]["result"]

def test_pipeline_remains_compatible_without_proposed_action():
    result=run([rainfall("r1",80)],NOW)
    assert result["proposed_action"] is None
    assert result["agents"]["guidelines"]["analysis"]["recommendation_check"]["proposed_recommendation"]

