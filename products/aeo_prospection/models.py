"""
AEO Prospection Models

Pydantic models for the AEO full-pipeline endpoint request and response.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class Competitor(BaseModel):
    """A competitor entry as stored in companies.competitors JSONB."""
    aliases: List[str] = Field(default_factory=list)
    website_url: str


class AEOPipelineRequest(BaseModel):
    """Request body for POST /prospect/run-full-pipeline."""
    company_name: str
    company_domain: str
    competitors: List[Competitor] = Field(default_factory=list)
    prompts: List[str]
    prospect_name: str
    prospect_email: str
    prospect_company: str
    country: Optional[str] = None
    city: Optional[str] = None
    models: List[str] = Field(default_factory=lambda: ["chatgpt", "perplexity"])
    n_executions_per_model: int = 3
    business_aliases: Optional[List[str]] = None
