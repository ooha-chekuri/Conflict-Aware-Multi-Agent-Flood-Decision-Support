"""Conservative retrieval and rule-based guideline applicability assessment.

Lexical retrieval only proposes passages. A passage is relevant only when its
action category and stated scope/conditions match the proposed action and the
available situation evidence. This is not a legal or compliance determination.
"""
import hashlib
import json
import re
from pathlib import Path

import pymupdf

from ..models import AgentOutput, Evidence


class GuidelineComplianceAgent:
    name = "Guideline Compliance Agent"
    FLOOD_TERMS = {"flood", "flooding", "river", "inundation", "evacuation", "rainfall", "warning"}

    def __init__(self, path="data/raw/ndma_guidelines_management_of_floods.pdf"):
        self.path = Path(path)

    def passages(self):
        index = Path("data/guidelines/passages_v2.jsonl")
        if not index.exists():
            index = Path("data/guidelines/passages.jsonl")
        if index.exists():
            return [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not self.path.exists():
            return []
        out = []
        with pymupdf.open(self.path) as doc:
            for page_no, page in enumerate(doc, 1):
                for para in re.split(r"\n\s*\n", page.get_text("text")):
                    text = " ".join(para.split())
                    if len(text) > 80:
                        out.append({"source": self.path.name, "page": page_no, "section": None, "text": text})
        return out

    def retrieve(self, query, limit=5):
        terms = set(re.findall(r"[a-z]{4,}", query.casefold()))
        scored = []
        for passage in self.passages():
            if not passage.get("section"):
                continue
            words = set(re.findall(r"[a-z]{4,}", passage["text"].casefold()))
            score = len(terms & words)
            if score:
                scored.append((score, passage))
        return [passage for _, passage in sorted(scored, key=lambda x: (-x[0], x[1]["page"]))[:limit]]

    @staticmethod
    def _action_type(action):
        text = action.casefold()
        evacuation = bool(re.search(r"\b(evacuat\w*)\b", text))
        if evacuation and re.search(r"\b(patient|medical|casualt\w*|ambulance|paramedic)\b", text):
            return "medical_evacuation"
        if evacuation and re.search(r"\b(plan|planning|plans|sop|procedure)\b", text):
            return "evacuation_planning"
        if evacuation or re.search(r"\b(move residents|relocat\w*)\b", text):
            return "community_evacuation"
        return None

    @staticmethod
    def _provision_types(passage):
        section = (passage.get("section") or "").casefold()
        text = passage.get("text", "").casefold()
        types=set()
        medical_scope="patient evacuation plan" in section or ("heli" in text and "casualt" in text and "evacuat" in text)
        if medical_scope:
            types.add("medical_evacuation")
        if not medical_scope and ("evacuation plan" in section or re.search(r"prepar\w+\s+plans?.{0,180}emergency evacuation", text)):
            types.add("evacuation_planning")
        if "evacuation of flood affected communities" in text or "evacuation of flood-affected communities" in text:
            types.add("community_evacuation")
        return types

    @staticmethod
    def _flood_context(evidence):
        return any(
            any(term in (item.claim_type + " " + item.claim_text).casefold() for term in GuidelineComplianceAgent.FLOOD_TERMS)
            for item in evidence
        )

    @staticmethod
    def _explicit_contradiction(action, passage):
        """Only flag a contradiction for an explicit prohibition the action violates."""
        ptext = passage["text"].casefold()
        atext = action.casefold()
        patterns = (
            (r"evacuat\w*.{0,50}(?:shall|must)\s+not\s+begin\s+before\s+([^.;]+)",
             r"\bbegin\s+evacuation\b[^.;]{0,80}\bbefore\b"),
            (r"(?:shall|must)\s+not\s+(?:begin|start|initiate)\s+evacuation\s+before\s+([^.;]+)",
             r"\b(?:begin|start|initiate)\s+evacuation\b[^.;]{0,80}\bbefore\b"),
            (r"(?:shall|must)\s+not\s+evacuate\s+([^.;]+)", r"\bmust\s+evacuate\b"),
        )
        return any(re.search(prohibition, ptext) and re.search(violating_action, atext) for prohibition, violating_action in patterns)

    @staticmethod
    def _citation(passage):
        return {
            "source": passage["source"],
            "physical_pdf_page": passage["page"],
            "printed_page": passage.get("printed_page"),
            "section": passage.get("section"),
            "excerpt": passage["text"],
        }

    def analyze(self, evidence, query="flood response evacuation warning", recommendation=""):
        candidates = self.retrieve(query)
        action_type = self._action_type(recommendation)
        relevant = [p for p in candidates if action_type and action_type in self._provision_types(p)]
        context_text = " ".join((e.claim_type + " " + e.claim_text).casefold() for e in evidence)
        flood_context = self._flood_context(evidence)
        context_ids = [e.evidence_id for e in evidence if e.claim_type != "historical_context"]

        result = "insufficient_evidence"
        explanation = "The action, provision scope, or situation conditions cannot be matched from the supplied evidence; human review is required."
        assessment_basis = {"action_type": action_type, "context_evidence_ids": context_ids, "conditions_checked": [], "scope_checked": []}
        if evidence and not flood_context:
            result = "not_applicable"
            explanation = "The supplied evidence does not describe a flood-related situation; flood-guideline applicability cannot be established for this case."
        elif flood_context and action_type and relevant:
            if any(self._explicit_contradiction(recommendation, p) for p in relevant):
                result = "contradicted"
                explanation = "A relevant provision explicitly prohibits the proposed action under the stated condition. Human review is required before any response."
                assessment_basis["conditions_checked"].append("explicit provision prohibition compared with proposed action")
            elif action_type == "evacuation_planning":
                has_plan_scope = bool(re.search(r"\b(emergency|flood|community|organisation|organization|stakeholder)\b", recommendation.casefold()))
                situation_flood_related = bool(re.search(r"\b(flood|flooding|flood-threatened|flood affected|flood-affected)\b", context_text))
                assessment_basis["scope_checked"] = ["evacuation planning", "emergency/community/organization scope"]
                assessment_basis["conditions_checked"] = ["flood context present in cited evidence"]
                if has_plan_scope and situation_flood_related:
                    result = "supported"
                    explanation = "The cited provision explicitly discusses preparing plans for organizations involved in emergency evacuation, and the evidence describes a flood situation. This is textual support for human consideration, not a compliance finding."
                else:
                    explanation = "A passage on evacuation planning was found, but the proposed action or evidence does not establish the provision's scope and flood conditions."
            elif action_type == "medical_evacuation":
                casualty_context = bool(re.search(r"\b(casualt\w*|injur\w*|patient|medical evacuation)\b", context_text))
                recommendation_specific = bool(re.search(r"\b(ambulance|paramedic|medical|casualt\w*|patient)\b", recommendation.casefold()))
                assessment_basis["conditions_checked"] = ["flood-casualty/medical context in evidence"]
                assessment_basis["scope_checked"] = ["patient or casualty evacuation"]
                if casualty_context and recommendation_specific:
                    result = "supported"
                    explanation = "The proposed medical evacuation action and casualty context match the retrieved medical evacuation provision. This is textual support for human consideration, not a compliance finding."
                elif re.search(r"\b(no|none|zero)\s+(?:reported\s+)?(casualt\w*|injur\w*|patient)\b", context_text):
                    result = "not_applicable"
                    explanation = "The available situation evidence explicitly reports no patients or casualties, so this medical evacuation provision is not applicable to the stated case."
                else:
                    explanation = "The passage concerns medical evacuation, but the evidence does not establish the casualty or patient conditions needed to apply it."
            elif action_type == "community_evacuation":
                warning_context = bool(re.search(r"\b(warning|alert|danger level|evacuation order)\b", context_text))
                already_affected = bool(re.search(r"\b(flooded|flood affected|flood-affected|inundat\w*)\b", context_text))
                action_has_condition = bool(re.search(r"\b(warning|alert|before impact|already flooded|flood affected|flood-affected)\b", recommendation.casefold()))
                assessment_basis["conditions_checked"] = ["warning/alert or already-affected-area context"]
                assessment_basis["scope_checked"] = ["flood-affected community evacuation"]
                if (warning_context or already_affected) and action_has_condition:
                    result = "supported"
                    explanation = "The provision describes evacuation of flood-affected communities based on warning indicators or after flooding; the proposed action and evidence state a compatible condition. This is textual support for human consideration, not a compliance finding."
                else:
                    explanation = "The provision covers community evacuation, but the required warning or already-affected condition is not established in both the action and situation evidence."

        assessment_abstained = result == "insufficient_evidence"
        candidate_citations = [self._citation(p) for p in candidates]
        relevant_citations = [self._citation(p) for p in relevant]
        claims = []
        for passage in candidates:
            digest = hashlib.sha256(passage["text"].encode("utf-8")).hexdigest()[:12]
            claims.append(Evidence(
                evidence_id=f"GUIDELINE-{passage['page']}-{digest}",
                source_name=passage["source"], source_class="official_guideline", source_label="guideline",
                claim_type="guideline", claim_text=passage["text"], measurement_type="guideline",
                source_page=passage["page"], section=passage.get("section"), verified=True,
                completeness=1.0, claim_confidence=.3,
                metadata={"retrieval_status": "candidate_only", "relevant_to_action": passage in relevant,
                          "printed_page": passage.get("printed_page")},
            ))
        check = {
            "proposed_recommendation": recommendation,
            "result": result,
            "assessment_abstained": assessment_abstained,
            "human_review_required": result in {"contradicted", "insufficient_evidence", "not_applicable"},
            "classification_scope": "provision-to-action applicability assessment; not a legal/regulatory compliance determination",
            "explanation": explanation,
            "action_type": action_type,
            "assessment_basis": assessment_basis,
            "relevant_provisions": relevant_citations,
            "retrieved_candidate_citations": candidate_citations,
            # Compatibility key: now only genuinely relevant provisions are included.
            "guideline_citations": relevant_citations,
            "matched_candidate_sections": relevant_citations,
            "method": "lexical retrieval followed by explicit action-category, scope, condition, and evidence-context rules; unresolved cases abstain",
        }
        provenance = [{"source": p["source"], "physical_pdf_page": p["page"], "section": p.get("section"), "excerpt": p["text"]} for p in candidates]
        out = AgentOutput(
            agent=self.name,
            claims=claims,
            findings=[{"type": "retrieved_candidate", "detail": p} for p in candidates]
                     + [{"type": "relevant_provision", "detail": p} for p in relevant],
            uncertainties=["Applicability is assessed conservatively; human review is required for unsupported or contradictory recommendations."],
            provenance=provenance,
            analysis={
                "retrieved_candidates": candidates,
                "relevant_provisions": relevant,
                "recommendation_check": check,
                "summary": f"Retrieved {len(candidates)} candidates; {len(relevant)} matched the proposed action category and scope.",
                "applicability": result,
            },
        )
        return out.model_dump(mode="json")
