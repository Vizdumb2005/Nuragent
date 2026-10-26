"""Prospect Qualifier Agent for Mistral Studio."""

from __future__ import annotations

from typing import Any

from mistralai.client import models as mistralai_models


class ProspectQualifierAgent:
    """Agent specialized in qualifying prospects based on evidence.
    
    This agent can be configured in Mistral Studio and invoked through the API.
    """
    
    AGENT_NAME = "nurafinix-prospect-qualifier"
    AGENT_DESCRIPTION = "Qualifies business prospects based on collected evidence and service fit"
    AGENT_MODEL = "mistral-small-latest"
    
    SYSTEM_PROMPT = """You are a lead qualification specialist for Nurafinix Labs.

Your task is to assess whether a business is a good fit for our services and whether there is genuine demand.

Our service categories:
- Data analytics, SQL, Python, and reporting dashboards
- Web development, software features, and integrations
- Business process and workflow automation
- AI/ML engineering and data engineering

Rules:
1. Only use the provided evidence to support your assessment.
2. Cite evidence IDs and source URLs for every claim you make.
3. Do NOT invent evidence or claim purchasing intent without support.
4. Be conservative: if uncertain, state it explicitly.
5. Focus on verifiable, actionable signals.

Output JSON with all required fields:
- fit_score: 0-25 (how well they match our services)
- demand_score: 0-30 (evidence of direct demand)
- opportunity_score: 0-25 (verified technical/operational opportunity)
- contact_score: 0-10 (legitimate contact channel availability)
- evidence_strength: description of evidence quality
- relevant_opportunities: list of specific opportunities
- uncertainty: 0-1 (how uncertain the assessment is)
- recommended_action: next step (e.g., "generate draft", "more research", "reject")
- cited_evidence: list of evidence IDs used
- reasoning: detailed explanation with citations
"""
    
    @classmethod
    def get_definition(cls) -> dict[str, Any]:
        """Get the agent definition for Studio configuration."""
        return {
            "name": cls.AGENT_NAME,
            "description": cls.AGENT_DESCRIPTION,
            "model": cls.AGENT_MODEL,
            "system_prompt": cls.SYSTEM_PROMPT,
            "input_schema": {
                "type": "object",
                "properties": {
                    "business": {
                        "type": "object",
                        "properties": {
                            "business_id": {"type": "string"},
                            "name": {"type": "string"},
                            "website": {"type": "string"},
                            "description": {"type": "string"},
                            "categories": {"type": "array", "items": {"type": "string"}},
                            "location": {"type": "string"},
                            "size": {"type": "string"},
                        },
                    },
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "evidence_id": {"type": "string"},
                                "category": {"type": "string"},
                                "observation": {"type": "string"},
                                "source_url": {"type": "string"},
                                "status": {"type": "string"},
                                "confidence": {"type": "number"},
                            },
                        },
                    },
                    "service_profile": {
                        "type": "string",
                        "default": "Data analytics, SQL, Python, reporting dashboards; Web development, software features, integrations; Business automation; AI/ML engineering, data engineering",
                    },
                },
                "required": ["business", "evidence"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "fit_score": {"type": "number", "minimum": 0, "maximum": 25},
                    "demand_score": {"type": "number", "minimum": 0, "maximum": 30},
                    "opportunity_score": {"type": "number", "minimum": 0, "maximum": 25},
                    "contact_score": {"type": "number", "minimum": 0, "maximum": 10},
                    "evidence_strength": {"type": "string"},
                    "relevant_opportunities": {"type": "array", "items": {"type": "string"}},
                    "uncertainty": {"type": "number", "minimum": 0, "maximum": 1},
                    "recommended_action": {"type": "string"},
                    "cited_evidence": {"type": "array", "items": {"type": "string"}},
                    "reasoning": {"type": "string"},
                },
                "required": [
                    "fit_score", "demand_score", "opportunity_score", "contact_score",
                    "evidence_strength", "relevant_opportunities", "uncertainty",
                    "recommended_action", "cited_evidence", "reasoning"
                ],
            },
        }
    
    @classmethod
    def create_request(
        cls,
        business: dict[str, Any],
        evidence: list[dict[str, Any]],
        service_profile: str | None = None,
    ) -> mistralai_models.ChatCompletionRequest:
        """Create a chat completion request for this agent."""
        import json
        
        business_json = json.dumps(business)
        evidence_json = json.dumps(evidence)
        
        user_message = (
            f"Business:\n{business_json}\n\n"
            f"Evidence:\n{evidence_json}\n\n"
            f"Service Profile:\n{service_profile or cls.get_definition()['input_schema']['properties']['service_profile']['default']}\n\n"
            "Output JSON with all required fields."
        )
        
        return mistralai_models.ChatCompletionRequest(
            model=cls.AGENT_MODEL,
            messages=[
                mistralai_models.SystemMessage(content=cls.SYSTEM_PROMPT),
                mistralai_models.UserMessage(content=user_message),
            ],
            response_format={"type": "json_object"},
        )
