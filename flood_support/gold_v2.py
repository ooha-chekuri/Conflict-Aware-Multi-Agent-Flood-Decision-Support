"""Separate, explicit author-adjudicated rules for synthetic v2 labels."""
import json
from pathlib import Path

RULES={
 "agreement":("none","escalate_for_human_verification"),
 "direct_status_conflict":("direct_contradiction","abstain"),
 "numeric_disagreement":("numerical_measurement","abstain"),
 "stale_update":("temporal_staleness","review_stale_evidence"),
 "geo_mismatch":("geographic_mismatch","abstain"),
 "road_status_conflict":("status_conflict","abstain"),
 "insufficient":("insufficient_evidence","abstain"),
 "independent_corroboration":("none","escalate_for_human_verification"),
 "flood_type_transfer":("none","escalate_for_human_verification")}

def create_gold(evidence,path="data/evaluation/labels/synthetic_gold_v2.jsonl",seed=2026):
    groups={}
    for e in evidence: groups.setdefault(e.scenario_id,[]).append(e)
    rows=[]
    for sid,items in groups.items():
        families={e.metadata.get("scenario_family") for e in items}
        if len(families)!=1: raise ValueError(f"mixed scenario families in {sid}")
        family=families.pop()
        conflict,outcome=RULES[family]
        rows.append({"scenario_id":sid,"scenario_family":family,"expected_conflict_type":conflict,"gold_outcome":outcome,"label_method":"independent author rulebook in gold_v2.RULES; rules declared before evaluation, not externally adjudicated","seed":seed})
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text("".join(json.dumps(r)+"\n" for r in rows),encoding="utf-8")
    return rows
