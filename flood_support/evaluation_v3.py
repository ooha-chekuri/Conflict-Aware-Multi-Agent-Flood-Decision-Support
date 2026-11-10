"""Family-held-out evaluation for corrected source-identity v3 evidence."""
from .evaluation_v2 import evaluate_v2

def evaluate_v3():
    return evaluate_v2(
        evidence_path="data/synthetic/evidence_v3.jsonl",
        gold_path="data/evaluation/labels/synthetic_gold_v3.jsonl",
        output_path="data/processed/evaluation_results_v3.json",
        version="v3",
    )
