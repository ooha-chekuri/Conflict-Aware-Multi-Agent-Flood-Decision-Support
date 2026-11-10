"""Transparent evidence sufficiency and human-review decision logic."""
import json
from pathlib import Path
from datetime import datetime, timezone
from .models import Evidence
from .conflicts import detect_conflicts
from .temporal import availability_state, validity_reference, age_hours
from .geography import geographic_relevance

_CONFIG = Path(__file__).resolve().parents[1] / "config" / "source_reliability.json"

def _settings():
    try:
        data=json.loads(_CONFIG.read_text(encoding="utf-8"))
        return data.get("weights",{}), data.get("decision",{})
    except (OSError, ValueError):
        return {}, {}

def analyze(evidence: list[Evidence], decision_time: datetime | None = None, location: str | None = None, guideline_feedback=None):
    now=decision_time or datetime.now(timezone.utc)
    weights, cfg=_settings()
    min_weight=float(cfg.get("minimum_evidence_weight",.25)); min_complete=float(cfg.get("minimum_completeness",.5))
    stale=float(cfg.get("stale_after_hours",12))
    conflicts=detect_conflicts(evidence,now,stale)
    rows=[]; supporting=[]; contradicting=[]; usable=[]
    for e in evidence:
        base=float(weights.get(e.source_class,weights.get("unknown",.4)))
        availability, avail_reason=availability_state(e,now)
        geo, geo_state, geo_reason=geographic_relevance(e,location,evidence)
        ref, ref_name=validity_reference(e)
        age=age_hours(ref,now) if ref else None
        reasons=[f"source prior={base:.2f} ({e.source_class}); {avail_reason}",geo_reason,f"completeness={e.completeness:.2f}"]
        if e.measurement_type == "forecast":
            start=e.forecast_valid_period_start or e.forecast_valid_at
            end=e.forecast_valid_period_end or e.forecast_valid_at
            forecast_valid=bool(end and end.tzinfo and now.tzinfo and (start is None or (start.tzinfo and now>=start)) and now<=end)
            temporal_ok=availability=="available" and forecast_valid
            if not forecast_valid: reasons_forecast="forecast is expired or not yet valid at decision time"
            else: reasons_forecast="forecast validity period includes decision time"
            reasons.append(reasons_forecast)
        else:
            temporal_ok=availability=="available" and age is not None and 0<=age<=stale
        complete_ok=e.completeness>=min_complete
        score=base*max(0,min(1,e.completeness))*geo
        if not temporal_ok: reasons.append(f"not eligible for current support: {ref_name} age={age}; availability={availability}")
        if not complete_ok: reasons.append(f"below configured completeness minimum {min_complete:.2f}")
        if score < min_weight: reasons.append(f"weight {score:.3f} below configured minimum {min_weight:.2f}")
        unverified_block=bool(cfg.get("unverified_sources_require_human_review",True) and e.source_class=="unverified_report" and not e.verified)
        eligible=temporal_ok and complete_ok and geo>0 and score>=min_weight and not unverified_block
        if unverified_block: reasons.append("unverified report is not eligible to support a current recommendation")
        row={"evidence_id":e.evidence_id,"source_name":e.source_name,"weight":round(score,4),"source_prior":base,"availability":availability,"availability_reason":avail_reason,"temporal_reference":ref_name,"age_hours":age,"geographic_relevance":geo,"geography_status":geo_state,"eligible_for_current_support":eligible,"reasons":reasons}
        rows.append(row)
        if eligible: usable.append(e); supporting.append(e.evidence_id)
    high=[c for c in conflicts if c.severity=="high"]
    unresolved=high
    unresolved_geo=any(c.conflict_type=="geographic_mismatch" for c in conflicts)
    contradictory_ids={i for c in high for i in c.evidence_ids}
    contradicting=sorted(contradictory_ids)
    # Explicit warning thresholds are immutable evidence, never overridden by model prose.
    above_danger=any(e.claim_type=="river_level_above_danger" and e.status not in {"false","no","below"} for e in usable)
    incident_claims=[e for e in usable if e.claim_type in {"flooding","road_access","evacuation","incident_status"} and e.status]
    by_source={}
    for e in incident_claims: by_source[e.source_name]=max(by_source.get(e.source_name,0),next((r["weight"] for r in rows if r["evidence_id"]==e.evidence_id),0))
    support_weight=sum(by_source.values())
    independent_sources={e.source_name for e in incident_claims if e.metadata.get("independent_source") is True}
    bonus=min(float(cfg.get("independent_corroboration_bonus",.1))*max(0,len(independent_sources)-1),.3)
    support_weight+=bonus
    minimum_support=float(cfg.get("minimum_recommendation_support",.45))
    verified_incident=bool(incident_claims) and support_weight>=minimum_support
    recommendation="Escalate for human verification" if above_danger or verified_incident else "Insufficient evidence for a current operational recommendation"
    abstain=not usable or bool(unresolved) or unresolved_geo or (not above_danger and not verified_incident)
    if guideline_feedback and guideline_feedback.get("result")=="contradicted":
        abstain=True
    if abstain: recommendation="Abstain and request human review"
    # This is a transparent sufficiency indicator, not calibrated probability.
    confidence=round(sum(r["weight"] for r in rows if r["eligible_for_current_support"])/max(1,len(rows)),3)
    limitations=["Decision support only; a human responder retains authority.","Unknown publication availability, ambiguous timezones, stale observations, incomplete evidence, or uncertain geography cannot support a current decision.","Unverified report-class evidence is not eligible; synthetic evidence is for evaluation only.","Confidence is not empirically calibrated."]
    if guideline_feedback and guideline_feedback.get("result") in {"insufficient_evidence","not_applicable"}:
        limitations.append("Guideline applicability was not established; any output is limited to referral for human verification and is not an operational instruction.")
    return {"recommendation":recommendation,"confidence":confidence,"confidence_interpretation":"uncalibrated evidence sufficiency indicator; not a probability","abstain":abstain,"human_review_required":True,"conflicts":[c.model_dump(mode="json") for c in conflicts],"evidence_weights":rows,"supporting_evidence":supporting,"contradicting_evidence":contradicting,"support_aggregation":{"distinct_source_weight":round(support_weight-bonus,3),"independent_source_count":len(independent_sources),"corroboration_bonus":round(bonus,3),"minimum_support":minimum_support,"passes_threshold":verified_incident or above_danger,"duplicate_rule":"multiple claims from one source name contribute only that source's maximum weight"},"label":"review" if abstain else "escalate","limitations":limitations,"guideline_feedback":guideline_feedback}
