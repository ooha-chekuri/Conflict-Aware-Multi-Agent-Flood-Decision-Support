import argparse,json
from pathlib import Path
from .ingest import prepare
from .synthetic import write
from .evaluation import evaluate
from .synthetic_v2 import write_evidence
from .gold_v2 import create_gold
from .evaluation_v2 import evaluate_v2
from .models import Evidence
from .synthetic_v3 import write_evidence_v3
from .gold_v3 import create_gold_v3
from .evaluation_v3 import evaluate_v3

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("prepare")
    sub.add_parser("prepare-v2")
    g=sub.add_parser("generate"); g.add_argument("--count",type=int,default=240); g.add_argument("--seed",type=int,default=42)
    e=sub.add_parser("evaluate"); e.add_argument("--llm-baseline",action="store_true",help="Call OpenAI once per held-out synthetic scenario; requires enabled API access and may incur charges.")
    g2=sub.add_parser("generate-v2"); g2.add_argument("--count",type=int,default=360); g2.add_argument("--seed",type=int,default=2026)
    sub.add_parser("evaluate-v2")
    g3=sub.add_parser("generate-v3"); g3.add_argument("--count",type=int,default=360); g3.add_argument("--seed",type=int,default=2026)
    sub.add_parser("evaluate-v3")
    a=p.parse_args()
    if a.cmd=="prepare": print(json.dumps(prepare(),indent=2))
    elif a.cmd=="prepare-v2": print(json.dumps(prepare(versioned_only=True),indent=2))
    elif a.cmd=="generate": print(f"Generated {write(a.count,a.seed)}")
    elif a.cmd=="generate-v2":
        write_evidence(count=a.count,seed=a.seed)
        evidence=[Evidence.model_validate_json(x) for x in Path("data/synthetic/evidence_v2.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        print(f"Generated {len(evidence)} evidence rows and {len(create_gold(evidence))} versioned gold labels")
    elif a.cmd=="evaluate-v2": print(json.dumps({k:v for k,v in evaluate_v2().items() if k!="rows"},indent=2))
    elif a.cmd=="generate-v3":
        write_evidence_v3(count=a.count,seed=a.seed)
        evidence=[Evidence.model_validate_json(x) for x in Path("data/synthetic/evidence_v3.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        print(f"Generated {len(evidence)} evidence rows and {len(create_gold_v3(evidence))} v3 gold labels")
    elif a.cmd=="evaluate-v3": print(json.dumps({k:v for k,v in evaluate_v3().items() if k!="rows"},indent=2))
    else:
        result=evaluate(use_llm=a.llm_baseline); print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))
if __name__=="__main__": main()
