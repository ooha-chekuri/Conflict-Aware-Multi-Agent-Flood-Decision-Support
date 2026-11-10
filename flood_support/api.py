from fastapi import FastAPI
from pathlib import Path
import json
from .models import AnalysisRequest
from .pipeline import run

app=FastAPI(title="Conflict-Aware Flood Decision Support",version="0.1.0",description="Research decision support; human authority retained.")
@app.get("/health")
def health(): return {"status":"ok","mode":"deterministic_local_demo","decision_support_only":True}
@app.post("/analyze")
def analyze(req:AnalysisRequest): return run(req.evidence,req.decision_time,req.location,req.proposed_action)
@app.get("/synthetic/scenarios")
def synthetic():
    p=Path("data/synthetic/evidence_v3.jsonl")
    if not p.exists(): p=Path("data/synthetic/evidence_v2.jsonl")
    if not p.exists(): p=Path("data/synthetic/evidence.jsonl")
    return {"records":[json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]} if p.exists() else {"records":[]}
@app.get("/historical/summary")
def historical():
    p=Path("data/processed/inspection_report_v2.json")
    if not p.exists(): p=Path("data/processed/inspection_report.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"message":"Run prepare first."}
