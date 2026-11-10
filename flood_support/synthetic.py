import json, random, argparse
from datetime import datetime,timedelta,timezone
from pathlib import Path
from .models import Evidence

PLACES=[("Riverside","riverine"),("Eastbank","riverine"),("Hilltown","flash"),("Coast Ward 3","coastal"),("Pine Valley","dam-release"),("Delta North","urban-pluvial")]
FAMILIES=["consistent","direct_contradiction","numerical_conflict","stale_report","geographic_mismatch","evacuation_road_status","insufficient","corroboration","varied_flood_type"]

def generate(count=240,seed=42):
    rng=random.Random(seed); base=datetime(2025,7,16,12,tzinfo=timezone.utc); records=[]; labels=[]
    for n in range(count):
        family=FAMILIES[n%len(FAMILIES)]; place,flood_type=PLACES[(n//len(FAMILIES))%len(PLACES)]; sid=f"SYN-{n:05d}"; loc=place if family!="geographic_mismatch" else place
        at=base+timedelta(hours=rng.randrange(0,8000)); kind="flooding"; rows=[]; expected="none"; outcome="review"
        def add(k,who,status=None,value=None,location=loc,hours=0,unit=None):
            rows.append(Evidence(evidence_id=f"{sid}-E{len(rows)+1}",scenario_id=sid,source_name=who,source_class="synthetic",source_label="synthetic",claim_type=k,claim_text=f"Fictional {k} report: {status if status is not None else value}",location=location,reported_at=at+timedelta(hours=hours),observed_at=at+timedelta(hours=hours),value=value,unit=unit,status=status,measurement_type="observation" if value is not None else "report",verified=who.startswith("Simulated official"),completeness=rng.choice([0.5,0.7,1.0]),metadata={"event_id":sid,"flood_type":flood_type}))
        if family in ("consistent","corroboration","varied_flood_type"):
            add(kind,"Simulated official field desk","flooded"); add(kind,"Fictional local responder","flooded")
            if family=="corroboration": add(kind,"Fictional independent agency","flooded")
            outcome="escalate_for_human_verification"
        elif family=="direct_contradiction": add(kind,"Simulated official field desk","flooded"); add(kind,"Fictional local report","not flooded"); expected="direct_contradiction"; outcome="abstain"
        elif family=="numerical_conflict": kind="rainfall"; add(kind,"Simulated gauge A",value=80,unit="mm/hour"); add(kind,"Fictional gauge B",value=25,unit="mm/hour"); expected="numerical_measurement"; outcome="verify_measurement"
        elif family=="stale_report": add(kind,"Fictional old report","flooded",hours=-48); add("road_access","Recent local report","closed",hours=0); expected="temporal_staleness"; outcome="review_stale_evidence"
        elif family=="geographic_mismatch": add(kind,"Simulated field report","flooded",location=place); add(kind,"Fictional district summary","not flooded",location=place+" District"); expected="none_geographic_mismatch"; outcome="do_not_compare"
        elif family=="evacuation_road_status": kind="road_access"; add(kind,"Simulated control room","closed"); add(kind,"Fictional driver report","open"); expected="status_conflict"; outcome="abstain"
        else: add(kind,"Fictional anonymous report",None); expected="insufficient_evidence"; outcome="abstain"
        records.extend(rows); labels.append({"scenario_id":sid,"expected_conflict_type":expected,"gold_outcome":outcome,"flood_type":flood_type,"scenario_family":family,"seed":seed})
    return records,labels

def write(count=240,seed=42,out="data/synthetic"):
    path=Path(out); path.mkdir(parents=True,exist_ok=True); rows,labels=generate(count,seed)
    (path/"evidence.jsonl").write_text("".join(x.model_dump_json()+"\n" for x in rows),encoding="utf-8")
    (Path("data/evaluation/labels")/"synthetic_gold.jsonl").write_text("".join(json.dumps(x)+"\n" for x in labels),encoding="utf-8")
    return len(rows),len(labels)

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--count",type=int,default=240); p.add_argument("--seed",type=int,default=42); a=p.parse_args(); print(write(a.count,a.seed))
