"""Synthetic v3 generator with validated source identity semantics."""
import json
import random
from pathlib import Path

from .synthetic_v2 import SOURCES, generate_evidence

INDEPENDENT_FAMILIES={"agreement","independent_corroboration","flood_type_transfer"}

def validate_source_independence(evidence):
    groups={}
    for item in evidence:
        groups.setdefault(item.scenario_id,[]).append(item)
    for scenario_id,items in groups.items():
        independent=[item for item in items if item.metadata.get("independent_source") is True]
        if not independent:
            continue
        by_name={}
        for item in items:
            if not item.source_name.strip():
                raise ValueError(f"empty source identity in {scenario_id}")
            by_name.setdefault(item.source_name.casefold(),set()).add(item.metadata.get("independent_source") is True)
        if any(len(flags)>1 for flags in by_name.values()):
            raise ValueError(f"source identity has inconsistent independence markers in {scenario_id}")
        names=[item.source_name.casefold() for item in independent]
        if len(independent)<2 or len(set(names))!=len(names):
            raise ValueError(f"independent-source markers require at least two distinct source names in {scenario_id}")
    return True

def generate_evidence_v3(count=360,seed=2026):
    evidence=generate_evidence(count,seed)
    rng=random.Random(seed+3)
    grouped={}
    for item in evidence:
        grouped.setdefault(item.scenario_id,[]).append(item)
    for sid,items in grouped.items():
        family=items[0].metadata["scenario_family"]
        new_sid=sid.replace("SYN2-","SYN3-")
        if family in INDEPENDENT_FAMILIES:
            if len(items)>len(SOURCES):
                raise ValueError(f"not enough distinct source names for {sid}")
            names=rng.sample(SOURCES,len(items))
            for item,name in zip(items,names):
                item.source_name=name
                item.metadata["independent_source"]=True
        for item in items:
            item.evidence_id=item.evidence_id.replace("SYN2-","SYN3-")
            item.scenario_id=new_sid
            item.metadata["generator_version"]="v3"
    validate_source_independence(evidence)
    return evidence

def write_evidence_v3(path="data/synthetic/evidence_v3.jsonl",count=360,seed=2026):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    evidence=generate_evidence_v3(count,seed)
    p.write_text("".join(item.model_dump_json()+"\n" for item in evidence),encoding="utf-8")
    return len(evidence)
