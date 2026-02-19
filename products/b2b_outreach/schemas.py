"""
Pydantic Schemas for LLM Structured Output
===========================================

These models define the expected JSON response shape for LLM calls that
need structured output. Used with shared.llm_utils.query_structured().

Note: Domain models (CompanyResearch, CompanySignals, etc.) are Pydantic
BaseModel classes in models.py. These schemas are specifically for LLM
structured output parsing via shared.llm_utils.query_structured().
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CompanyInfoResponse(BaseModel):
    """Schema for LLM-extracted company information from website analysis."""
    # Core profile
    name: str = Field(description="Company official name")
    industry: str = Field(description="Primary industry (e.g., 'SaaS', 'E-commerce', 'Consulting')")
    products: List[str] = Field(default_factory=list, description="List of main products")
    services: List[str] = Field(default_factory=list, description="List of main services")
    value_proposition: str = Field(default="", description="Core value proposition (1-2 sentences)")
    target_audience: str = Field(default="", description="Primary target audience (e.g., 'B2B SMBs', 'Enterprise')")
    pain_points: List[str] = Field(default_factory=list, description="Customer pain points the company solves")
    country: Optional[str] = Field(default=None, description="Country code if mentioned (e.g., 'US', 'CL')")
    city: Optional[str] = Field(default=None, description="City if mentioned")
    aliases: Optional[List[str]] = Field(default=None, description="Alternative company names or brands")
    competitors: Optional[List[str]] = Field(default=None, description="Mentioned competitors if any")
    # B2B sales intelligence
    business_context: Optional[List[str]] = Field(default=None, description="Key business highlights: revenue, investment plans, growth metrics, recent announcements")
    strategic_priorities: Optional[List[str]] = Field(default=None, description="Current strategic focus areas: digital transformation, international expansion, AI adoption, cost reduction, etc.")
    company_challenges: Optional[List[str]] = Field(default=None, description="The company's OWN operational challenges and pain points — not their customers' problems")
    tech_stack: Optional[List[str]] = Field(default=None, description="Known technologies, platforms, and tools the company uses")
    buying_triggers: Optional[List[str]] = Field(default=None, description="Recent events creating purchase opportunities: new leadership, expansion, digital transformation, regulatory changes")
    annual_revenue: Optional[str] = Field(default=None, description="Annual revenue figure (e.g., 'US$13B')")
    employee_count: Optional[str] = Field(default=None, description="Approximate employee count (e.g., '100,000+')")


class DiscoveryPromptsResponse(BaseModel):
    """Schema for LLM-generated discovery prompts."""
    prompts: List[str] = Field(description="List of realistic product discovery search queries")
