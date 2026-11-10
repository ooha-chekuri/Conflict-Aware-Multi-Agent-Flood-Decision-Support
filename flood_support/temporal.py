"""Explicit temporal semantics. Unknown or timezone-ambiguous times are not guessed."""
from datetime import datetime, timezone
from .models import Evidence

def availability_state(e: Evidence, decision_time: datetime) -> tuple[str, str]:
    available=e.available_at
    if available is None:
        return "unknown", "source publication/availability time is not established"
    if available.tzinfo is None or decision_time.tzinfo is None:
        return "unknown", "availability or decision timestamp lacks an explicit timezone"
    if available > decision_time:
        return "future", "evidence became available after the decision time"
    return "available", "available_at is at or before the decision time"

def validity_reference(e: Evidence):
    """Return the correct temporal endpoint for freshness; forecasts use validity, not report time."""
    if e.measurement_type == "forecast":
        if e.forecast_valid_period_end: return e.forecast_valid_period_end, "forecast_valid_period_end"
        if e.forecast_valid_at: return e.forecast_valid_at, "forecast_valid_at"
        return None, "forecast validity unknown"
    if e.observation_period_end: return e.observation_period_end, "observation_period_end"
    if e.observed_at: return e.observed_at, "observed_at"
    if e.report_as_of_time: return e.report_as_of_time, "report_as_of_time"
    if e.reported_at: return e.reported_at, "reported_at"
    return None, "observation/report time unknown"

def age_hours(reference: datetime, decision_time: datetime):
    if reference.tzinfo is None or decision_time.tzinfo is None:
        return None
    return (decision_time-reference).total_seconds()/3600
