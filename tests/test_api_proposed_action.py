from datetime import datetime, timezone
from fastapi.testclient import TestClient
from flood_support.api import app

def payload():
    now=datetime(2026,1,1,tzinfo=timezone.utc).isoformat()
    item={"evidence_id":"api-flood","source_name":"District Desk","source_class":"field_verified","source_label":"synthetic","claim_type":"flooding","claim_text":"Flood-affected communities are preparing an emergency evacuation plan.","location":"Test Village","observed_at":now,"reported_at":now,"available_at":now,"status":"flooded","measurement_type":"report","verified":True,"completeness":1}
    return {"evidence":[item],"decision_time":now,"location":"Test Village"}

def test_api_accepts_optional_proposed_action_and_returns_assessment():
    client=TestClient(app)
    legacy=client.post("/analyze",json=payload())
    assert legacy.status_code==200
    assert legacy.json()["proposed_action"] is None
    action="Prepare and validate emergency evacuation plans for all organisations serving flood-affected communities before impact."
    explicit=client.post("/analyze",json=payload()|{"proposed_action":action})
    assert explicit.status_code==200
    body=explicit.json()
    assert body["proposed_action"]==action
    assert body["agents"]["guidelines"]["analysis"]["recommendation_check"]["proposed_recommendation"]==action
    assert body["decision"]["guideline_feedback"]["result"]==body["agents"]["guidelines"]["analysis"]["recommendation_check"]["result"]
    assert body["decision"]["guideline_feedback"]["result"]=="supported"
