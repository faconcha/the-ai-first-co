import os
import logging
from typing import List

import requests

from products.b2b_outreach.enrichment import models as enrichment_models

logger = logging.getLogger(__name__)

# Map Hunter.io API result strings to our internal verification statuses
_RESULT_MAP = {
    'deliverable': enrichment_models.EmailVerificationStatus.VALID,
    'undeliverable': enrichment_models.EmailVerificationStatus.INVALID,
    'risky': enrichment_models.EmailVerificationStatus.CATCH_ALL,
}


def verify_email(email: str) -> enrichment_models.EmailVerificationStatus:
    """
    Verify email using Hunter.io email verifier.
    Requires HUNTER_API_KEY env var.
    """
    api_key = os.getenv('HUNTER_API_KEY')
    if not api_key:
        return enrichment_models.EmailVerificationStatus.UNKNOWN

    try:
        response = requests.get(
            'https://api.hunter.io/v2/email-verifier',
            params={
                'email': email,
                'api_key': api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        result = response.json().get('data', {}).get('result', '')
        return _RESULT_MAP.get(result, enrichment_models.EmailVerificationStatus.UNKNOWN)

    except Exception as e:
        logger.warning("Email verification failed for %s: %s", email, e)
        return enrichment_models.EmailVerificationStatus.UNKNOWN


def verify_contacts(contacts: List[enrichment_models.EnrichedContact]) -> List[enrichment_models.EnrichedContact]:
    """Verify emails for all contacts with emails. Updates email_verification field."""
    for contact in contacts:
        if contact.email:
            contact.email_verification = verify_email(contact.email)
    return contacts
