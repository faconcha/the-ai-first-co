from typing import Optional
from enum import Enum

from pydantic import BaseModel, model_validator


class ContactRole(str, Enum):
    CMO = "cmo"
    CEO = "ceo"
    VP_MARKETING = "vp_marketing"
    VP_PRODUCT = "vp_product"
    CTO = "cto"
    FOUNDER = "founder"
    OTHER = "other"


class EmailVerificationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    CATCH_ALL = "catch_all"


class EnrichedContact(BaseModel):
    name: str
    email: Optional[str] = None
    role: ContactRole
    domain: str
    company_name: str
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    twitter_handle: Optional[str] = None
    email_verification: EmailVerificationStatus = EmailVerificationStatus.UNKNOWN
    source: str = ""
    confidence_score: float = 0.0
    seniority: str = ""

    @model_validator(mode='after')
    def _auto_seniority(self):
        """Auto-assign seniority level from role if not explicitly set."""
        if not self.seniority:
            c_suite = {ContactRole.CEO, ContactRole.CMO, ContactRole.CTO, ContactRole.FOUNDER}
            director = {ContactRole.VP_MARKETING, ContactRole.VP_PRODUCT}
            if self.role in c_suite:
                self.seniority = 'c_suite'
            elif self.role in director:
                self.seniority = 'director'
            else:
                self.seniority = 'manager'
        return self
