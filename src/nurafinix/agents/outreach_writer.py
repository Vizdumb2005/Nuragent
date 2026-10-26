"""Outreach Writer Agent for Mistral Studio."""

from __future__ import annotations

from typing import Any

from mistralai.client import models as mistralai_models


class OutreachWriterAgent:
    """Agent specialized in writing personalized outreach drafts.
    
    This agent can be configured in Mistral Studio and invoked through the API.
    """
    
    AGENT_NAME = "nurafinix-outreach-writer"
    AGENT_DESCRIPTION = "Writes personalized, evidence-based outreach drafts for qualified prospects"
    AGENT_MODEL = "mistral-small-latest"
    
    SYSTEM_PROMPT = """You are an outreach specialist for Nurafinix Labs.

Your task is to write a concise, personalized outreach draft for a qualified lead.

Rules:
1. ONLY use information from the provided evidence.
2. Reference actual observations with their source URLs.
3. Explain the potential relevance of the observation to our services.
4. Propose a low-pressure next step (e.g., "Would you be open to a quick call?").
5. Do NOT invent personal familiarity, commercial relationships, or business outcomes.
6. Do NOT claim ROI, testimonials, or case studies we haven't provided.
7. Be professional, concise, and specific.
8. Keep the draft under 200 words.

Our services:
- Data analytics, SQL, Python, and reporting dashboards
- Web development, software features, and integrations
- Business process and workflow automation
- AI/ML engineering and data engineering

Output JSON with all required fields:
- subject: email subject line (max 60 characters)
- body: email body text
- service_offer: the service being offered
- evidence_references: list of evidence IDs cited
- source_urls: list of source URLs cited
- reasoning: brief explanation of why this draft is appropriate
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
                    "candidate": {
                        "type": "object",
                        "properties": {
                            "business_id": {"type": "string"},
                            "name": {"type": "string"},
                            "website": {"type": "string"},
                            "description": {"type": "string"},
                            "categories": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "score": {
                        "type": "object",
                        "properties": {
                            "total_score": {"type": "number"},
                            "priority": {"type": "string"},
                            "fit_score": {"type": "number"},
                            "demand_score": {"type": "number"},
                        },
                    },
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "evidence_id": {"type": "string"},
                                "observation": {"type": "string"},
                                "source_url": {"type": "string"},
                                "category": {"type": "string"},
                            },
                        },
                    },
                    "service_offer": {
                        "type": "string",
                        "default": "Data analytics and reporting dashboards",
                    },
                    "company_description": {
                        "type": "string",
                        "default": "Nurafinix Labs helps businesses unlock insights from their data through custom analytics, dashboards, and automation solutions.",
                    },
                },
                "required": ["candidate", "score", "evidence"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "maxLength": 60},
                    "body": {"type": "string"},
                    "service_offer": {"type": "string"},
                    "evidence_references": {"type": "array", "items": {"type": "string"}},
                    "source_urls": {"type": "array", "items": {"type": "string"}},
                    "reasoning": {"type": "string"},
                },
                "required": ["subject", "body", "service_offer", "evidence_references", "source_urls", "reasoning"],
            },
        }
    
    @classmethod
    def create_request(
        cls,
        candidate: dict[str, Any],
        score: dict[str, Any],
        evidence: list[dict[str, Any]],
        service_offer: str | None = None,
        company_description: str | None = None,
    ) -> mistralai_models.ChatCompletionRequest:
        """Create a chat completion request for this agent."""
        import json
        
        candidate_json = json.dumps(candidate)
        score_json = json.dumps(score)
        evidence_json = json.dumps(evidence)
        
        user_message = (
            f"Qualified Lead:\n{candidate_json}\n\n"
            f"Score:\n{score_json}\n\n"
            f"Evidence:\n{evidence_json}\n\n"
            f"Service Offer: {service_offer or cls.get_definition()['input_schema']['properties']['service_offer']['default']}\n\n"
            f"Company Description: {company_description or cls.get_definition()['input_schema']['properties']['company_description']['default']}\n\n"
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
