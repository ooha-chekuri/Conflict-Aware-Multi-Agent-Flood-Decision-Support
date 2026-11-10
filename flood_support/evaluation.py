import json,random
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
from .models import Evidence
from .conflicts import detect_conflicts
from .decision import analyze

def evaluate(data="data/synthetic/evidence.jsonl",labels="data/evaluation/labels/synthetic_gold.jsonl",seed=42,use_llm=False):
    ep=Path(data); lp=Path(labels)
    if not ep.exists() or not lp.exists(): return {"error":"Run `python -m flood_support.cli generate` first."}
    ev=[Evidence.model_validate_json(x) for x in ep.read_text(encoding="utf-8").splitlines() if x.strip()]; labs=[json.loads(x) for x in lp.read_text(encoding="utf-8").splitlines() if x.strip()]
    by={}
    for e in ev: by.setdefault(e.scenario_id,[]).append(e)
    scenarios=[x for x in labs if x["scenario_id"] in by]; rng=random.Random(seed); ids=[x["scenario_id"] for x in scenarios]; rng.shuffle(ids); cut=max(1,int(.8*len(ids))); train=set(ids[:cut]); test=set(ids[cut:])
    # Labels are author-created; split is persisted and never used to tune thresholds.
    rows=[]
    for lab in scenarios:
        sid=lab["scenario_id"]
        if sid not in test: continue
        es=by[sid]; now=max((e.reported_at for e in es if e.reported_at),default=datetime.now(timezone.utc)) + __import__('datetime').timedelta(hours=1)
        conflicts=detect_conflicts(es,now,12); found={c.conflict_type for c in conflicts}
        expected=lab["expected_conflict_type"]
        truth=expected not in {"none","none_geographic_mismatch","insufficient_evidence"}; pred=any(c.severity!="info" for c in conflicts)
        sys=analyze(es,now)
        # Single-agent heuristic baseline: strongest source-class incident claim, no cross-source conflict detection.
        incidents=[e for e in es if e.claim_type in {"flooding","road_access","evacuation","incident_status"}]
        single=bool(incidents and any((e.status or "").casefold() in {"flooded","closed","evacuated"} for e in sorted(incidents,key=lambda x:x.verified,reverse=True)[:1]))
        single_conflict=False
        if use_llm:
            from .llm import classify_scenario
            llm_outcome,single_conflict=classify_scenario(es)
            single=llm_outcome=="escalate_for_human_verification"
        # Majority baseline among status values; tie abstains.
        vals=Counter((e.status or "").casefold() for e in incidents if e.status); maj=vals.most_common()
        majority=bool(maj and (len(maj)==1 or maj[0][1]>maj[1][1]) and maj[0][0] in {"flooded","closed","evacuated"})
        majority_conflict=len(vals)>1
        gold_positive=lab["gold_outcome"]=="escalate_for_human_verification"
        rows.append({"scenario_id":sid,"split":"test","conflict_truth":truth,"conflict_pred":pred,"single_conflict_pred":single_conflict,"majority_conflict_pred":majority_conflict,"gold_positive":gold_positive,"system_positive":not sys["abstain"] and bool(sys["supporting_evidence"]),"single_positive":single,"majority_positive":majority,"abstain":sys["abstain"],"expected":expected,"found":sorted(found),"confidence":sys["confidence"],"provenance_complete":all(e.source_name and e.evidence_id and e.source_label and e.reported_at for e in es)})
    def metrics(predkey):
        tp=sum(r["conflict_truth"] and r[predkey] for r in rows); fp=sum(not r["conflict_truth"] and r[predkey] for r in rows); fn=sum(r["conflict_truth"] and not r[predkey] for r in rows)
        prec=tp/(tp+fp) if tp+fp else 0; rec=tp/(tp+fn) if tp+fn else 0
        return {"precision":round(prec,3),"recall":round(rec,3),"f1":round(2*prec*rec/(prec+rec),3) if prec+rec else 0}
    acc={k:round(sum(r[k]==r["gold_positive"] for r in rows)/len(rows),3) if rows else 0 for k in ["system_positive","single_positive","majority_positive"]}
    ece=None
    if rows:
        ece_value=0.0
        for bin_no in range(10):
            bucket=[r for r in rows if min(9,int(r["confidence"]*10))==bin_no]
            if bucket:
                mean_conf=sum(r["confidence"] for r in bucket)/len(bucket)
                observed_rate=sum(r["gold_positive"] for r in bucket)/len(bucket)
                ece_value+=(len(bucket)/len(rows))*abs(mean_conf-observed_rate)
        ece=round(ece_value,3)
    out={"seed":seed,"train_scenarios":len(train),"test_scenarios":len(test),"thresholds_tuned_on_test":False,"conflict_metrics":{"multi_agent":metrics("conflict_pred"),"single_agent":metrics("single_conflict_pred"),"majority_vote":metrics("majority_conflict_pred")},"decision_accuracy":acc,"single_agent_baseline":"OpenAI Responses API" if use_llm else "local deterministic proxy (enable --llm-baseline for OpenAI)","confidence_calibration_error_ece_diagnostic":ece,"provenance_completeness":round(sum(r["provenance_complete"] for r in rows)/len(rows),3) if rows else None,"abstention_rate":round(sum(r["abstain"] for r in rows)/len(rows),3) if rows else None,"abstain_on_gold_review_or_conflict":round(sum(r["abstain"] for r in rows if not r["gold_positive"])/max(1,sum(not r["gold_positive"] for r in rows)),3),"limitations":"Synthetic author-defined labels; local proxy results do not represent an external LLM. Confidence is an uncalibrated sufficiency indicator; ECE is diagnostic only. LLM calls are opt-in, billable, and not needed for core decisions.","rows":rows}
    Path("data/processed").mkdir(exist_ok=True); Path("data/processed/evaluation_results.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    return out
