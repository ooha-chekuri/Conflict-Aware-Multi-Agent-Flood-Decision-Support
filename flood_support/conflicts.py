from datetime import datetime, timezone
from .models import Evidence, Conflict
from .temporal import validity_reference, age_hours
from .geography import normalize_place
from .temporal import availability_state

def detect_conflicts(evidence: list[Evidence], decision_time: datetime | None = None, stale_after_hours: float = 12) -> list[Conflict]:
    """Deterministic comparisons only; incompatible time/location/type/unit are not contradictions."""
    now = decision_time or datetime.now(timezone.utc)
    out: list[Conflict] = []
    # Staleness is an evidence warning, not a claim that the underlying claim is false.
    for e in evidence:
        if availability_state(e,now)[0] != "available":
            continue
        if e.claim_type not in {"guideline","historical_context","inundation_map_context"} and e.status is None and e.value is None and len(e.claim_text.strip())<80:
            out.append(Conflict(conflict_type="insufficient_evidence",severity="medium",evidence_ids=[e.evidence_id],explanation="The available claim has no structured status or measurement and too little descriptive content to verify; do not infer a flood condition."))
        t, _ = validity_reference(e)
        if t and e.claim_type not in {"guideline", "historical_context"}:
            age = age_hours(t, now)
            if age is not None and age > stale_after_hours:
                out.append(Conflict(conflict_type="temporal_staleness", severity="medium", evidence_ids=[e.evidence_id], explanation=f"Evidence is {age:.1f} hours old at decision time; treat as historical context until refreshed."))
    for i, a in enumerate(evidence):
        for b in evidence[i+1:]:
            if availability_state(a,now)[0] != "available" or availability_state(b,now)[0] != "available": continue
            # Different named locations are not comparable unless exact normalized place matches.
            same_location=bool(normalize_place(a.location)) and normalize_place(a.location) == normalize_place(b.location)
            same_event=a.metadata.get("event_id") and a.metadata.get("event_id")==b.metadata.get("event_id")
            if not same_location:
                if same_event and a.claim_type==b.claim_type:
                    out.append(Conflict(conflict_type="geographic_mismatch",severity="info",evidence_ids=[a.evidence_id,b.evidence_id],explanation=f"Reports share event identifier {a.metadata.get('event_id')} but use different locations ({a.location} vs {b.location}); do not compare them as co-located evidence."))
                continue
            if a.claim_type != b.claim_type: continue
            station_a=a.metadata.get("station"); station_b=b.metadata.get("station")
            if station_a and station_b and str(station_a).strip().casefold()!=str(station_b).strip().casefold(): continue
            ta, _ = validity_reference(a); tb, _ = validity_reference(b)
            if ta and tb:
                if ta.tzinfo is None or tb.tzinfo is None: continue
                if abs((ta-tb).total_seconds()) > 3600: continue
            elif bool(ta) != bool(tb): continue
            if a.measurement_type != b.measurement_type: continue
            if a.value is not None and b.value is not None:
                if (a.unit or "").casefold() != (b.unit or "").casefold(): continue
                if abs(a.value-b.value) > max(0.1, 0.05*max(abs(a.value), abs(b.value))):
                    out.append(Conflict(conflict_type="numerical_measurement", severity="high", evidence_ids=[a.evidence_id,b.evidence_id], explanation=f"Comparable values differ ({a.value:g} vs {b.value:g} {a.unit or ''}); verify station, units and observation context."))
            elif a.status and b.status and a.status.casefold() != b.status.casefold():
                kind = "status_conflict" if a.claim_type in {"road_access","evacuation","incident_status"} else "direct_contradiction"
                out.append(Conflict(conflict_type=kind, severity="high", evidence_ids=[a.evidence_id,b.evidence_id], explanation=f"Sources report incompatible {a.claim_type} statuses: {a.status} vs {b.status}."))
    return out
