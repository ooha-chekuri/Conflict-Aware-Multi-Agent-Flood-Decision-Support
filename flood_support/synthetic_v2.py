"""Versioned synthetic evidence creation; labels are assigned separately."""
import random
from datetime import datetime, timedelta, timezone
from .models import Evidence

FAMILIES=("agreement","direct_status_conflict","numeric_disagreement","stale_update","geo_mismatch","road_status_conflict","insufficient","independent_corroboration","flood_type_transfer")
PLACES=("Nadiad East","Kota Ward 4","Pine Block","Delta Sector 8","Upper Basin Station","Coastal Hamlet")
SOURCES=("District Desk","Volunteer Network","Gauge Network","Local Control Room","Field Unit","Community Hotline")

def generate_evidence(count=360,seed=2026):
    rng=random.Random(seed); origin=datetime(2026,8,12,12,tzinfo=timezone.utc); output=[]
    for n in range(count):
        family=FAMILIES[n%len(FAMILIES)]; sid=f"SYN2-{n:05d}"; place=rng.choice(PLACES); base=origin+timedelta(days=rng.randrange(0,60),hours=rng.randrange(0,24)); rows=[]
        flood_type=rng.choice(("riverine","flash","coastal","urban_pluvial","dam_release"))
        def add(kind,source,status=None,value=None,unit=None,where=None,offset=0,independent=False):
            observed=base+timedelta(hours=offset)
            rows.append(Evidence(evidence_id=f"{sid}-E{len(rows)+1}",scenario_id=sid,source_name=source,source_class="synthetic",source_label="synthetic",claim_type=kind,claim_text=f"Fictional {kind} report: {status if status is not None else value}",location=where or place,observed_at=observed,reported_at=observed,available_at=observed,ingested_at=origin,value=value,unit=unit,status=status,measurement_type="observation" if value is not None else "report",completeness=rng.choice((.5,.7,1.0)),metadata={"scenario_family":family,"event_id":sid,"flood_type":flood_type,"independent_source":independent}))
        if family in ("agreement","independent_corroboration","flood_type_transfer"):
            add("flooding",rng.choice(SOURCES),"flooded")
            add("flooding",rng.choice(SOURCES),"flooded",independent=True)
            if family=="independent_corroboration": add("flooding",rng.choice(SOURCES),"flooded",independent=True)
        elif family=="direct_status_conflict":
            add("flooding",rng.choice(SOURCES),"flooded"); add("flooding",rng.choice(SOURCES),rng.choice(("not flooded","water receded")))
        elif family=="numeric_disagreement":
            unit=rng.choice(("mm/hour","mm/h")); val=rng.randint(35,110)
            add("rainfall",rng.choice(SOURCES),value=val,unit=unit); add("rainfall",rng.choice(SOURCES),value=round(val*rng.uniform(.25,.55),1),unit=unit)
        elif family=="stale_update":
            add("flooding",rng.choice(SOURCES),"flooded",offset=-rng.choice((24,48,72))); add("road_access",rng.choice(SOURCES),rng.choice(("open","closed")))
        elif family=="geo_mismatch":
            add("flooding",rng.choice(SOURCES),"flooded",where=place+" Village"); add("flooding",rng.choice(SOURCES),"not flooded",where=place+" District")
        elif family=="road_status_conflict":
            add("road_access",rng.choice(SOURCES),"closed"); add("road_access",rng.choice(SOURCES),"open")
        else:
            add("flooding",rng.choice(SOURCES),None)
        output.extend(rows)
    return output

def write_evidence(path="data/synthetic/evidence_v2.jsonl",count=360,seed=2026):
    from pathlib import Path
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); data=generate_evidence(count,seed)
    p.write_text("".join(x.model_dump_json()+"\n" for x in data),encoding="utf-8")
    return len(data)
