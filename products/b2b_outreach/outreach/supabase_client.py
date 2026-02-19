"""
Supabase Client
===============

Client for the `prospects` table: contact lookup and signal persistence.

Table schema: see products/b2b_outreach/config/supabase_schema.sql
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from supabase import create_client, Client

logger = logging.getLogger(__name__)


def _get_client() -> Optional[Client]:
    """Create Supabase client from env vars. Returns None if not configured."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        return None
    return create_client(url, key)


def find_prospects_by_company(company_name: str, domain: str) -> List[Dict[str, Any]]:
    """
    Fetch all prospects matching a company domain or name from the prospects table.

    Tries exact domain match first, then falls back to case-insensitive company name match.
    Returns empty list if Supabase is not configured or no match found.
    """
    client = _get_client()
    if not client:
        logger.warning("Supabase not configured — skipping prospect lookup")
        return []

    try:
        response = client.table('prospects').select('*').eq('company_url', domain).execute()
        if response.data:
            return response.data

        response = client.table('prospects').select('*').ilike('company_name', company_name).execute()
        return response.data if response.data else []

    except Exception as e:
        logger.warning("Error fetching prospects for %s (%s): %s", company_name, domain, e)
        return []


def save_prospect_signals(prospect_id: str, signals_dict: Dict[str, Any]) -> bool:
    """
    Update a prospect's signals data and detection timestamp in Supabase.

    Returns True on success, False if Supabase is not configured or the request fails.
    """
    client = _get_client()
    if not client:
        return False

    try:
        client.table('prospects').update({
            'signals': signals_dict,
            'signals_detected_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', prospect_id).execute()
        return True

    except Exception as e:
        logger.warning("Error saving signals for prospect %s: %s", prospect_id, e)
        return False


def get_prospect_by_id(prospect_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single prospect by ID.

    Returns None if not found or Supabase is not configured.
    Used by message_generator to resolve a contact name from a Supabase ID.
    """
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('prospects').select('*').eq('id', prospect_id).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error fetching prospect %s: %s", prospect_id, e)
        return None
