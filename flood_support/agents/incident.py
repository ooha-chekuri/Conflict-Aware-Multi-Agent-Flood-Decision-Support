from ..models import AgentOutput

class IncidentVerificationAgent:
    name = "Incident Verification Agent"
    def analyze(self, evidence):
        selected=[e for e in evidence if e.claim_type in {"flooding","road_access","evacuation","rescue","incident_status","damage","affected_districts","affected_locations","affected_population","relief_shelter"}]
        seen=set(); duplicates=[]
        for e in selected:
            key=(e.claim_type,(e.location or "").casefold(),(e.status or e.claim_text).casefold())
            if key in seen: duplicates.append(e.evidence_id)
            seen.add(key)
        locations={}
        for e in selected:
            event=e.metadata.get("event_id")
            if event and e.location: locations.setdefault(event,set()).add(e.location.casefold())
        mismatches=[event for event,locs in locations.items() if len(locs)>1]
        provenance=[{"evidence_id":e.evidence_id,"source_name":e.source_name,"source_page":e.source_page,"source_label":e.source_label} for e in selected]
        findings=[{"type":"duplicate_candidate","evidence_id":x} for x in duplicates]+[{"type":"geographic_mismatch","event_id":x} for x in mismatches]
        out=AgentOutput(agent=self.name,claims=selected,findings=findings,uncertainties=["Duplicate and geographic findings are candidates for review, not verified source errors."],provenance=provenance,analysis={"duplicate_candidates":duplicates,"geographic_mismatch_event_ids":mismatches,"summary":f"Reviewed {len(selected)} incident claims; {len(duplicates)} possible repeated claims and {len(mismatches)} event(s) with differing location labels."})
        return out.model_dump(mode="json")
