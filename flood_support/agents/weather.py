from ..models import AgentOutput

class WeatherRiskAgent:
    name = "Weather Risk Agent"
    def analyze(self, evidence):
        selected=[e for e in evidence if e.claim_type in {"rainfall","river_level","river_level_above_danger","flood_forecast","weather_forecast"}]
        observations=[e for e in selected if e.measurement_type=="observation" and e.value is not None and e.observed_at]
        groups={}
        for e in observations: groups.setdefault((e.claim_type,e.metadata.get("station") or e.location,e.unit),[]).append(e)
        trends=[]
        for (kind,loc,unit),items in groups.items():
            items.sort(key=lambda x:x.observed_at)
            if len({x.observed_at for x in items})<2: direction="insufficient_series"; delta=None
            else:
                delta=items[-1].value-items[0].value
                direction="rising" if delta>0 else "falling" if delta<0 else "steady"
            trends.append({"claim_type":kind,"location_or_station":loc,"unit":unit,"direction":direction,"change_first_to_last":delta,"evidence_ids":[x.evidence_id for x in items]})
        thresholds=[{"evidence_id":e.evidence_id,"location":e.location,"warning_level":e.metadata.get("warning_level_m"),"danger_level":e.metadata.get("danger_level_m"),"highest_flood_level":e.metadata.get("highest_flood_level_m"),"unit":"m","source":e.source_name,"page":e.source_page} for e in selected if any(k in e.metadata for k in ("warning_level_m","danger_level_m","highest_flood_level_m"))]
        observed=[e for e in selected if e.measurement_type=="observation"]
        forecasts=[e for e in selected if e.measurement_type=="forecast" or e.metadata.get("forecast_value_m") is not None]
        provenance=[{"evidence_id":e.evidence_id,"source_name":e.source_name,"source_page":e.source_page,"source_label":e.source_label} for e in selected]
        findings=[{"type":"trend","detail":x} for x in trends]+[{"type":"thresholds","detail":x} for x in thresholds]
        uncertainties=["No risk prediction is produced.","Trend comparison requires multiple compatible observations at the same location and unit.","No absent river-level or threshold values are inferred."]
        out=AgentOutput(agent=self.name,claims=selected,findings=findings,uncertainties=uncertainties,provenance=provenance,analysis={"observed_claim_ids":[e.evidence_id for e in observed],"forecast_claim_ids":[e.evidence_id for e in forecasts],"trends":trends,"thresholds":thresholds,"summary":f"Reviewed {len(observed)} observed and {len(forecasts)} forecast claims; observations remain distinct from forecasts."})
        return out.model_dump(mode="json")
