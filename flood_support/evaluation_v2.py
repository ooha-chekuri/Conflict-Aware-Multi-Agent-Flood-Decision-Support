"""Family-held-out evaluation that writes only versioned outputs."""
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path
from .models import Evidence
from .conflicts import detect_conflicts
from .decision import analyze

TEST_FAMILIES={"agreement","geo_mismatch","road_status_conflict","insufficient"}
OUTCOMES=("escalate_for_human_verification","abstain","no_escalation","review_stale_evidence")

def _binary(truth,pred):
    tp=sum(t and p for t,p in zip(truth,pred)); fp=sum((not t) and p for t,p in zip(truth,pred)); fn=sum(t and not p for t,p in zip(truth,pred)); tn=sum((not t) and not p for t,p in zip(truth,pred))
    precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
    return {"confusion_matrix":{"tn":tn,"fp":fp,"fn":fn,"tp":tp},"precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0}

def _per_class(labels,pred):
    result={}
    for label in sorted(set(labels)|set(pred)):
        t=[x==label for x in labels]; p=[x==label for x in pred]; m=_binary(t,p)
        result[label]={"precision":m["precision"],"recall":m["recall"],"f1":m["f1"],"support":sum(t)}
    return result

def _single_agent(entities):
    # Independent local classifier: exact-location, same-claim status/value comparisons.
    for i,a in enumerate(entities):
        for b in entities[i+1:]:
            if (a.location or "").casefold()!=(b.location or "").casefold() or a.claim_type!=b.claim_type: continue
            if a.status and b.status and a.status.casefold()!=b.status.casefold(): return True
            if a.value is not None and b.value is not None and (a.unit or "").casefold()==(b.unit or "").casefold() and abs(a.value-b.value)>max(.1,.05*max(abs(a.value),abs(b.value))): return True
    return False

def evaluate_v2(evidence_path="data/synthetic/evidence_v2.jsonl",gold_path="data/evaluation/labels/synthetic_gold_v2.jsonl",output_path="data/processed/evaluation_results_v2.json",version="v2"):
    evidence=[Evidence.model_validate_json(x) for x in Path(evidence_path).read_text(encoding="utf-8").splitlines() if x.strip()]
    labels=[json.loads(x) for x in Path(gold_path).read_text(encoding="utf-8").splitlines() if x.strip()]
    groups={}
    for e in evidence: groups.setdefault(e.scenario_id,[]).append(e)
    if set(x["scenario_id"] for x in labels)!=set(groups): raise ValueError("evidence and gold scenario IDs do not match")
    if not TEST_FAMILIES.issubset({x["scenario_family"] for x in labels}): raise ValueError("held-out families are missing")
    train=[x for x in labels if x["scenario_family"] not in TEST_FAMILIES]; test=[x for x in labels if x["scenario_family"] in TEST_FAMILIES]
    rows=[]
    for gold in test:
        items=groups[gold["scenario_id"]]; decision_time=max(e.available_at for e in items if e.available_at)+timedelta(hours=1)
        found=detect_conflicts(items,decision_time); conflict_pred=any(c.severity!="info" for c in found)
        baseline_single=_single_agent(items)
        # Majority operates on the dominant status and abstains on ties; it does not read scenario labels.
        status_groups={}
        for e in items:
            if e.status: status_groups.setdefault((e.claim_type,(e.location or "").casefold()),Counter())[(e.status or "").casefold()]+=1
        majority_conflict=any(len(vals)>1 and vals.most_common()[0][1]==vals.most_common()[1][1] for vals in status_groups.values())
        result=analyze(items,decision_time)
        prediction="abstain" if result["abstain"] else "escalate_for_human_verification"
        positive_statuses={"flooded","closed","evacuated","above danger"}
        single_outcome="abstain" if baseline_single else ("escalate_for_human_verification" if any((e.status or "").casefold() in positive_statuses for e in items) else "no_escalation")
        # Majority vote is location- and claim-specific. Ties abstain; a strict majority decides status.
        votes=[]
        for values in status_groups.values():
            ranked=values.most_common()
            if len(ranked)>1 and ranked[0][1]==ranked[1][1]: votes.append("abstain")
            elif ranked:
                votes.append("escalate_for_human_verification" if ranked[0][0] in positive_statuses else "no_escalation")
        majority_outcome="abstain" if "abstain" in votes else (Counter(votes).most_common(1)[0][0] if votes else "no_escalation")
        predicted_types=sorted({c.conflict_type for c in found if c.severity!="info" or c.conflict_type=="geographic_mismatch"})
        rows.append({"scenario_id":gold["scenario_id"],"family":gold["scenario_family"],"truth_conflict":gold["expected_conflict_type"] not in {"none","geographic_mismatch"},"truth_conflict_type":gold["expected_conflict_type"],"pred_conflict_type":predicted_types[0] if predicted_types else "none","pred_conflict":conflict_pred,"single_conflict":baseline_single,"majority_conflict":majority_conflict,"gold_outcome":gold["gold_outcome"],"pred_outcome":prediction,"single_outcome":single_outcome,"majority_outcome":majority_outcome,"abstain":result["abstain"],"confidence_sufficiency":result["confidence"]})
    truth=[r["truth_conflict"] for r in rows]
    outcome_metrics={}
    for name,pred_key in (("system","pred_outcome"),("local_single_agent","single_outcome"),("majority_vote","majority_outcome")):
        preds=[r[pred_key] for r in rows]
        outcome_metrics[name]={"accuracy":sum(pred==r["gold_outcome"] for r,pred in zip(rows,preds))/len(rows) if rows else None,"class_wise":_per_class([r["gold_outcome"] for r in rows],preds),"confusion_matrix":{actual:{guess:sum(r["gold_outcome"]==actual and r[pred_key]==guess for r in rows) for guess in OUTCOMES} for actual in OUTCOMES}}
    coverage=sum(not r["abstain"] for r in rows)/len(rows) if rows else None
    conflict_types=sorted({r["truth_conflict_type"] for r in rows}|{r["pred_conflict_type"] for r in rows})
    type_confusion={actual:{guess:sum(r["truth_conflict_type"]==actual and r["pred_conflict_type"]==guess for r in rows) for guess in conflict_types} for actual in conflict_types}
    provenance=sum(bool(e.evidence_id and e.source_name and e.source_label and e.scenario_id) for e in evidence)/len(evidence) if evidence else None
    out={"evaluation_version":version,"split_method":f"scenario-generation family holdout; fixed held-out families declared in evaluation_{version}.TEST_FAMILIES","train_families":sorted({r["scenario_family"] for r in train}),"test_families":sorted(TEST_FAMILIES),"train_scenarios":len(train),"test_scenarios":len(rows),"metrics":{"conflict_detection":{"system":_binary(truth,[r["pred_conflict"] for r in rows]),"local_single_agent":_binary(truth,[r["single_conflict"] for r in rows]),"majority_vote":_binary(truth,[r["majority_conflict"] for r in rows]),"multi_class_conflict_type":{"accuracy":sum(r["truth_conflict_type"]==r["pred_conflict_type"] for r in rows)/len(rows) if rows else None,"class_wise":_per_class([r["truth_conflict_type"] for r in rows],[r["pred_conflict_type"] for r in rows]),"confusion_matrix":type_confusion}},"decision_outcome":outcome_metrics,"abstention":{"coverage":coverage,"abstention_rate":1-coverage if coverage is not None else None,"abstain_on_gold_abstain":sum(r["abstain"] and r["gold_outcome"]=="abstain" for r in rows)/max(1,sum(r["gold_outcome"]=="abstain" for r in rows))},"provenance_completeness":provenance,"confidence_calibration_error":None},"confidence_note":"Evidence sufficiency only; no calibration metric is claimed until probabilities are calibrated on disjoint data; calibration field is null by design.","gold_limitations":"Labels use a separate explicit author rulebook but have not been independently adjudicated by domain experts; four families are held out and the synthetic generator remains artificial.","binary_definition":"Contradiction detection excludes geographic mismatch (a comparability warning, not a contradiction); insufficiency is included as an evidence conflict.","rows":rows}
    p=Path(output_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2),encoding="utf-8")
    return out
