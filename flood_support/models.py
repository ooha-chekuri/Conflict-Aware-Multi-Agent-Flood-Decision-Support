from datetime import date, datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    evidence_id: str
    scenario_id: str | None = None
    source_name: str
    source_class: str = "unknown"
    source_label: Literal["historical", "synthetic", "live", "guideline"] = "historical"
    claim_type: str
    claim_text: str
    location: str | None = None
    location_level: str | None = None
    admin_hierarchy: dict[str, str] = Field(default_factory=dict)
    latitude: float | None = None
    longitude: float | None = None
    observed_at: datetime | None = None
    observation_period_start: datetime | None = None
    observation_period_end: datetime | None = None
    reported_at: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    ingested_at: datetime | None = None
    forecast_valid_at: datetime | None = None
    forecast_valid_period_start: datetime | None = None
    forecast_valid_period_end: datetime | None = None
    forecast_valid_date: date | None = None
    report_as_of_time: datetime | None = None
    availability_assumption: dict | None = None
    value: float | None = None
    unit: str | None = None
    status: str | None = None
    measurement_type: Literal["observation", "forecast", "report", "guideline", "unknown"] = "unknown"
    source_page: int | None = None
    section: str | None = None
    verified: bool = False
    completeness: float = Field(default=0.6, ge=0, le=1)
    claim_confidence: float = Field(default=0.5, ge=0, le=1)
    metadata: dict = Field(default_factory=dict)

class Conflict(BaseModel):
    conflict_type: str
    severity: str
    evidence_ids: list[str]
    explanation: str

class AgentOutput(BaseModel):
    """Typed output that references original source evidence without cloning it."""
    agent: str
    claims: list[Evidence] = Field(default_factory=list)
    findings: list[dict | str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    provenance: list[dict] = Field(default_factory=list)
    analysis: dict = Field(default_factory=dict)

class AnalysisRequest(BaseModel):
    evidence: list[Evidence]
    decision_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location: str | None = None
    proposed_action: str | None = None
    location_level: str | None = None
    admin_hierarchy: dict[str, str] = Field(default_factory=dict)

