import pytest
from flood_support.models import Evidence
from flood_support.synthetic_v3 import generate_evidence_v3, validate_source_independence
from flood_support.gold_v3 import create_gold_v3

def test_v3_generator_emits_distinct_source_identities_for_independent_reports():
    records=generate_evidence_v3(90,2026)
    assert validate_source_independence(records)
    by={}
    for item in records: by.setdefault(item.scenario_id,[]).append(item)
    for items in by.values():
        marked=[item for item in items if item.metadata.get("independent_source") is True]
        if marked:
            assert len(marked)>=2
            assert len({item.source_name for item in marked})==len(marked)
            assert all(item.metadata["generator_version"]=="v3" for item in items)

def test_source_validation_rejects_duplicate_independence_metadata():
    base=dict(scenario_id="bad",source_class="synthetic",source_label="synthetic",claim_type="flooding",claim_text="fiction",location="A",available_at="2026-01-01T00:00:00Z",status="flooded",metadata={"independent_source":True})
    items=[Evidence(evidence_id="a",source_name="Same desk",**base),Evidence(evidence_id="b",source_name="Same desk",**base)]
    with pytest.raises(ValueError,match="distinct source names"):
        validate_source_independence(items)

def test_v3_gold_writer_is_separate_and_versioned(tmp_path):
    records=generate_evidence_v3(18,4)
    labels=create_gold_v3(records,tmp_path/"synthetic_gold_v3.jsonl",4)
    assert labels and all(label["label_version"]=="v3" for label in labels)
    assert (tmp_path/"synthetic_gold_v3.jsonl").exists()
