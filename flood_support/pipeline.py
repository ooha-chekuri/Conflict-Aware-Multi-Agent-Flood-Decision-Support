from .agents import WeatherRiskAgent, IncidentVerificationAgent, GuidelineComplianceAgent
from .decision import analyze

def collect_unique_agent_claims(*agent_outputs):
    """Combine agent references by source evidence ID; repeated agent references count once."""
    unique={}
    for output in agent_outputs:
        for claim in output["claims"]:
            prior=unique.get(claim["evidence_id"])
            if prior is not None and prior!=claim:
                raise ValueError(f"Agents returned inconsistent claim payloads for evidence {claim['evidence_id']}")
            unique[claim["evidence_id"]]=claim
    from .models import Evidence
    return [Evidence.model_validate(value) for value in unique.values()]

def run(evidence,decision_time,location=None,proposed_action=None):
    weather=WeatherRiskAgent().analyze(evidence)
    incident=IncidentVerificationAgent().analyze(evidence)
    agent_claims=collect_unique_agent_claims(weather,incident)
    preliminary=analyze(agent_claims,decision_time,location=location)
    action_to_assess=proposed_action or preliminary["recommendation"]
    query=f"{location or ''} {action_to_assess} " + " ".join(e.claim_text for e in agent_claims[:8])
    guidelines=GuidelineComplianceAgent().analyze(agent_claims,query=query,recommendation=action_to_assess)
    decision=analyze(agent_claims,decision_time,location=location,guideline_feedback=guidelines["analysis"].get("recommendation_check"))
    return {"situation":location or "All supplied locations","proposed_action":proposed_action,"raw_evidence":[e.model_dump(mode="json") for e in evidence],"agents":{"weather":weather,"incident":incident,"guidelines":guidelines},"decision":decision}
