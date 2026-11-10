"""Optional OpenAI single-agent baseline, isolated from the deterministic decision path."""
import os,json
from dotenv import load_dotenv
from openai import OpenAI
from .models import Evidence

def classify_scenario(evidence:list[Evidence]):
    load_dotenv()
    if os.getenv("LLM_ENABLED", "false").casefold() != "true":
        raise RuntimeError("Set LLM_ENABLED=true to explicitly enable paid single-agent baseline calls.")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for the optional LLM baseline.")
    model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client=OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    records=[{"id":e.evidence_id,"source":e.source_name,"type":e.claim_type,"location":e.location,"time":e.observed_at.isoformat() if e.observed_at else None,"value":e.value,"unit":e.unit,"status":e.status,"claim":e.claim_text} for e in evidence]
    response=client.responses.create(
        model=model,
        instructions=("You are a single-agent research baseline for fictional flood-response evidence. "
                      "Classify only the provided evidence. Contradictions or missing information require abstain_review. "
                      "Never issue autonomous emergency instructions. Do not add facts or thresholds."),
        input="Classify the scenario using this evidence JSON: "+json.dumps(records,ensure_ascii=False),
        text={"format":{"type":"json_schema","name":"baseline_decision","strict":True,"schema":{"type":"object","properties":{"outcome":{"type":"string","enum":["escalate_for_human_verification","abstain_review"]},"conflict_detected":{"type":"boolean"}},"required":["outcome","conflict_detected"],"additionalProperties":False}}},
        max_output_tokens=100,
    )
    result=json.loads(response.output_text)
    return result["outcome"],result["conflict_detected"]
