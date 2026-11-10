from datetime import datetime,timezone,timedelta
from flood_support.models import Evidence
from flood_support.conflicts import detect_conflicts
from flood_support.synthetic import generate
from flood_support.decision import analyze

NOW=datetime(2025,1,1,tzinfo=timezone.utc)
def ev(i,**kw):
    base=dict(evidence_id=i,source_name=i,source_class="unverified_report",source_label="synthetic",claim_type="flooding",claim_text="fiction",location="A",observed_at=NOW,reported_at=NOW,available_at=NOW,status="flooded",measurement_type="report")
    return Evidence(**(base|kw))

def test_detect_direct_status_conflict():
    cs=detect_conflicts([ev("a"),ev("b",status="not flooded")],NOW)
    assert any(c.conflict_type=="direct_contradiction" for c in cs)

def test_geographic_mismatch_not_compared():
    assert not detect_conflicts([ev("a"),ev("b",location="B",status="not flooded")],NOW)

def test_linked_mismatched_locations_flagged_without_contradiction():
    a=ev("a",metadata={"event_id":"evt-1"})
    b=ev("b",location="B",status="not flooded",metadata={"event_id":"evt-1"})
    cs=detect_conflicts([a,b],NOW)
    assert len(cs)==1 and cs[0].conflict_type=="geographic_mismatch" and cs[0].severity=="info"

def test_numeric_requires_same_units_and_time():
    a=ev("a",claim_type="rainfall",value=80,unit="mm",status=None)
    b=ev("b",claim_type="rainfall",value=5,unit="in",status=None)
    assert not detect_conflicts([a,b],NOW)

def test_stale_marked():
    assert any(c.conflict_type=="temporal_staleness" for c in detect_conflicts([ev("a",observed_at=NOW-timedelta(days=2))],NOW))

def test_synthetic_variety_and_label_separation():
    records,labels=generate(45,4)
    assert len(labels)==45 and len(records)>45
    assert all(e.source_label=="synthetic" and e.evidence_id and e.scenario_id for e in records)
    assert all("gold_outcome" in x for x in labels)

def test_abstention_and_human_authority():
    result=analyze([ev("a")],NOW)
    assert result["abstain"] and result["human_review_required"]

def test_timezone_naive_timestamps_are_not_guessed_for_conflicts():
    a=ev("a",observed_at=datetime(2025,1,1),available_at=datetime(2025,1,1))
    b=ev("b",observed_at=datetime(2025,1,1),available_at=datetime(2025,1,1),status="not flooded")
    assert not detect_conflicts([a,b],NOW)
    assert analyze([a],NOW)["abstain"]

def test_future_availability_cannot_support_decision():
    future=ev("a",available_at=NOW+timedelta(hours=1))
    result=analyze([future],NOW)
    assert result["abstain"]
    assert result["evidence_weights"][0]["availability"]=="future"

def test_future_evidence_does_not_create_present_conflict():
    a=ev("a",available_at=NOW,status="flooded")
    b=ev("b",available_at=NOW+timedelta(minutes=10),status="not flooded")
    assert not detect_conflicts([a,b],NOW)

def test_exact_location_required_for_scoped_support():
    result=analyze([ev("a",available_at=NOW)],NOW,location="B")
    assert result["abstain"]
    assert result["evidence_weights"][0]["geography_status"]=="uncertain"

def test_historical_observation_availability_does_not_refresh_stale_content():
    old=ev("a",observed_at=NOW-timedelta(days=2),available_at=NOW)
    result=analyze([old],NOW)
    assert result["abstain"]
    assert not result["evidence_weights"][0]["eligible_for_current_support"]

def test_expired_forecast_cannot_support_current_decision():
    expired=ev("f",claim_type="flooding",measurement_type="forecast",observed_at=None,
               forecast_valid_at=NOW-timedelta(hours=2),available_at=NOW-timedelta(hours=3))
    result=analyze([expired],NOW)
    assert result["abstain"]
    assert not result["evidence_weights"][0]["eligible_for_current_support"]

def test_currently_valid_forecast_uses_validity_not_report_age():
    forecast=ev("f",claim_type="flooding",measurement_type="forecast",observed_at=None,
                forecast_valid_period_start=NOW-timedelta(hours=1),forecast_valid_period_end=NOW+timedelta(hours=4),
                available_at=NOW-timedelta(days=4),source_class="government_official")
    result=analyze([forecast],NOW)
    assert result["evidence_weights"][0]["eligible_for_current_support"]

def test_weight_threshold_and_independent_corroboration_change_outcome():
    from flood_support.synthetic_v2 import generate_evidence
    single=generate_evidence(9,21) # first family is agreement; the generator yields two reports
    # Keep one claim to measure a single low-reliability source contribution.
    one=single[0].model_copy(update={"completeness":.5,"metadata":{"independent_source":False}})
    result_one=analyze([one],one.available_at+timedelta(hours=1))
    pair=[single[0].model_copy(update={"metadata":{"independent_source":True}}),single[1].model_copy(update={"metadata":{"independent_source":True}})]
    result_pair=analyze(pair,pair[0].available_at+timedelta(hours=1))
    assert result_one["abstain"]
    assert result_pair["support_aggregation"]["corroboration_bonus"]>0

def test_high_numerical_conflict_requires_review():
    a=ev("a",claim_type="rainfall",value=80,unit="mm",status=None,available_at=NOW)
    b=ev("b",claim_type="rainfall",value=20,unit="mm",status=None,available_at=NOW)
    result=analyze([a,b],NOW)
    assert result["abstain"]
    assert any(c["conflict_type"]=="numerical_measurement" for c in result["conflicts"])

def test_guideline_uncertainty_does_not_block_referral_for_human_verification():
    supported=ev("incident",source_class="field_verified",available_at=NOW,verified=True,completeness=1)
    result=analyze([supported],NOW,guideline_feedback={"result":"insufficient_evidence"})
    assert not result["abstain"]
    assert result["human_review_required"]
    assert any("Guideline applicability was not established" in x for x in result["limitations"])

def test_guideline_contradiction_still_blocks_recommendation():
    supported=ev("incident",source_class="field_verified",available_at=NOW,verified=True,completeness=1)
    result=analyze([supported],NOW,guideline_feedback={"result":"contradicted"})
    assert result["abstain"]

def test_guideline_citation_preserves_source_and_physical_page(monkeypatch):
    from flood_support.agents.guideline import GuidelineComplianceAgent
    from flood_support.models import Evidence
    agent=GuidelineComplianceAgent()
    monkeypatch.setattr(agent,"retrieve",lambda query,limit=5:[{"source":"ndma.pdf","page":89,"section":"8.1.3 Evacuation Plan","printed_page":76,"text":"Preparing plans for all organizations involved in emergency evacuation of flood-affected communities is required."}])
    item=ev("g",claim_type="flooding",claim_text="Flood conditions are reported and evacuation plans are being prepared.",available_at=NOW)
    result=agent.analyze([item],query="emergency evacuation plan flood organization",recommendation="Prepare and validate emergency evacuation plans for all organizations serving flood-affected communities before impact")
    check=result["analysis"]["recommendation_check"]
    assert check["result"]=="supported"
    assert check["guideline_citations"][0]["source"]=="ndma.pdf"
    assert check["guideline_citations"][0]["physical_pdf_page"]==89
    assert "not a legal/regulatory compliance determination" in check["classification_scope"]
    assert result["claims"][0]["source_name"]=="ndma.pdf"
    assert result["claims"][0]["source_page"]==89

def test_v2_scenario_families_are_disjoint_by_split_and_metrics_are_multiclass(tmp_path):
    from flood_support.synthetic_v2 import generate_evidence
    from flood_support.gold_v2 import create_gold
    from flood_support.evaluation_v2 import evaluate_v2, TEST_FAMILIES
    evidence=generate_evidence(90,12)
    ep=tmp_path/"ev.jsonl"; lp=tmp_path/"labels.jsonl"; out=tmp_path/"metrics.json"
    ep.write_text("".join(x.model_dump_json()+"\n" for x in evidence),encoding="utf-8")
    create_gold(evidence,lp,12)
    result=evaluate_v2(ep,lp,out)
    assert not (set(result["train_families"]) & set(result["test_families"]))
    assert set(result["test_families"])==TEST_FAMILIES
    assert "confusion_matrix" in result["metrics"]["decision_outcome"]["system"]
    assert "local_single_agent" in result["metrics"]["decision_outcome"]
    assert "majority_vote" in result["metrics"]["decision_outcome"]
    assert out.exists()
