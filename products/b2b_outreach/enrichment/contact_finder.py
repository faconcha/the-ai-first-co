"""
Contact Finder
==============

Look up decision-maker contacts from the Supabase prospects table.
LinkedIn scraping is a future enhancement for filling missing fields.
"""

import logging
from typing import List, Optional, Dict

from products.b2b_outreach.enrichment import models as enrichment_models
from products.b2b_outreach.outreach import supabase_client

logger = logging.getLogger(__name__)

ROLE_KEYWORDS: Dict[enrichment_models.ContactRole, List[str]] = {
    enrichment_models.ContactRole.CEO: [
        # English
        'chief executive', 'ceo', 'general manager',
        # Spanish / LATAM
        'director ejecutivo', 'director general', 'gerente general',
        'presidente ejecutivo', 'director gerente',
    ],
    enrichment_models.ContactRole.CMO: [
        # English
        'chief marketing', 'cmo', 'marketing officer',
        # Spanish / LATAM
        'director de marketing', 'gerente de marketing', 'jefe de marketing',
        'director comercial y marketing', 'director de mercadeo',
        'gerente de mercadeo', 'jefe de mercadeo',
    ],
    enrichment_models.ContactRole.VP_MARKETING: [
        # English
        'vp marketing', 'vice president marketing', 'head of marketing', 'marketing director',
        # Spanish / LATAM
        'gerente comercial', 'director comercial', 'jefe comercial',
        'gerente de ventas y marketing', 'subdirector de marketing',
    ],
    enrichment_models.ContactRole.VP_PRODUCT: [
        # English
        'vp product', 'vice president product', 'head of product', 'product director',
        # Spanish / LATAM
        'director de producto', 'gerente de producto', 'jefe de producto',
        'director de productos', 'gerente de productos',
    ],
    enrichment_models.ContactRole.CTO: [
        # English
        'chief technology', 'cto', 'technology officer',
        # Spanish / LATAM
        'director de tecnología', 'director tecnológico', 'gerente de tecnología',
        'jefe de tecnología', 'director de sistemas', 'gerente de sistemas',
        'director de ti', 'gerente de ti',
    ],
    enrichment_models.ContactRole.FOUNDER: [
        # English
        'founder', 'co-founder',
        # Spanish / LATAM
        'fundador', 'co-fundador', 'cofundador', 'socio fundador',
    ],
}

ROLE_PRIORITY: Dict[enrichment_models.ContactRole, int] = {
    enrichment_models.ContactRole.CEO: 0,
    enrichment_models.ContactRole.CMO: 1,
    enrichment_models.ContactRole.VP_MARKETING: 2,
    enrichment_models.ContactRole.VP_PRODUCT: 3,
    enrichment_models.ContactRole.FOUNDER: 4,
    enrichment_models.ContactRole.CTO: 5,
    enrichment_models.ContactRole.OTHER: 6,
}


def _map_title_to_role(title: str) -> enrichment_models.ContactRole:
    """Map a job title string to a ContactRole enum using keyword matching."""
    title_lower = title.lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if any(kw in title_lower for kw in keywords):
            return role
    return enrichment_models.ContactRole.OTHER


def find_contacts(
    company_name: str,
    domain: str,
    roles: Optional[List[enrichment_models.ContactRole]] = None,
) -> List[enrichment_models.EnrichedContact]:
    """
    Find decision-maker contacts for a company from Supabase.

    Returns contacts matching the requested roles (default: all roles).
    Returns empty list if Supabase is not configured or no prospects found.

    Future: LinkedIn scraping as a fallback for missing fields (phone, email).
    """
    prospects = supabase_client.find_prospects_by_company(company_name, domain)
    if not prospects:
        logger.info("No prospects found in Supabase for %s (%s)", company_name, domain)
        return []

    target_roles = set(roles) if roles else None

    contacts: List[enrichment_models.EnrichedContact] = []
    for prospect in prospects:
        person_job = prospect.get('person_job') or ''
        role = _map_title_to_role(person_job)

        if target_roles and role not in target_roles:
            continue

        email = prospect.get('person_email') or None
        contact = enrichment_models.EnrichedContact(
            name=prospect.get('person_name', 'Unknown'),
            email=email,
            role=role,
            domain=domain,
            company_name=company_name,
            phone=prospect.get('person_phone') or None,
            source='supabase',
            confidence_score=1.0,
            email_verification=(
                enrichment_models.EmailVerificationStatus.VALID if email
                else enrichment_models.EmailVerificationStatus.UNKNOWN
            ),
        )
        contacts.append(contact)

    contacts.sort(key=lambda c: ROLE_PRIORITY.get(c.role, 99))
    return contacts[:5]
