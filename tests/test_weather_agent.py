from datetime import datetime, timezone
from flood_support.agents.weather import WeatherRiskAgent
from flood_support.models import Evidence

def test_same_time_measurements_are_not_reported_as_a_trend():
    when=datetime(2026,1,1,tzinfo=timezone.utc)
    items=[Evidence(evidence_id=f"g{i}",source_name=f"source-{i}",source_class="official_telemetry",source_label="synthetic",claim_type="rainfall",claim_text="fictional gauge reading",location="Creek Gauge",observed_at=when,reported_at=when,available_at=when,value=value,unit="mm/hour",measurement_type="observation",metadata={"station":"Creek Gauge"}) for i,value in enumerate((70,25),1)]
    result=WeatherRiskAgent().analyze(items)
    trend=result["analysis"]["trends"][0]
    assert trend["direction"]=="insufficient_series"
    assert trend["change_first_to_last"] is None
    assert result["provenance"][0]["evidence_id"]=="g1"
