"""
Supabase Client
===============

CRUD operations for the B2B Outreach CRM tables:
- companies: Company profile (name, url, industry, country, city)
- contacts: People database (CRM contacts with roles)
- deals: Sales pipeline
- activities: Interaction log (emails, calls, meetings, notes)
- prospects: Outbound prospect database (email as PK, linked to companies)
- prospects_demo: AEO visibility results per prospect
- campaigns: Outreach campaign tracking
- campaign_contacts: Per-contact campaign enrollment + message status

Table schema: see products/b2b_outreach/config/supabase_schema.sql
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from supabase import create_client, Client

logger = logging.getLogger(__name__)


def _get_client() -> Optional[Client]:
    """Create Supabase client from env vars. Returns None if not configured."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        return None
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Companies (profile only — no pipeline data)
# ---------------------------------------------------------------------------


def upsert_company(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Insert or update a company by company_url.

    Uses company_url as the conflict key: if a company with the same URL exists,
    it updates the record; otherwise it inserts a new one.

    Returns the company record or None if Supabase is not configured.
    """
    client = _get_client()
    if not client:
        logger.warning("Supabase not configured — skipping company upsert")
        return None

    try:
        response = client.table('companies').upsert(
            data, on_conflict='company_url'
        ).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error upserting company: %s", e)
        return None


def find_company_by_url(company_url: str) -> Optional[Dict[str, Any]]:
    """Find a company by company_url. Returns None if not found."""
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('companies').select('*').eq('company_url', company_url).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error finding company %s: %s", company_url, e)
        return None


def get_company_by_id(company_id: str) -> Optional[Dict[str, Any]]:
    """Find a company by ID."""
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('companies').select('*').eq('id', company_id).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error fetching company %s: %s", company_id, e)
        return None


def update_company(company_id: str, data: Dict[str, Any]) -> bool:
    """Update company profile fields. Returns True on success."""
    client = _get_client()
    if not client:
        return False

    try:
        client.table('companies').update(data).eq('id', company_id).execute()
        return True

    except Exception as e:
        logger.warning("Error updating company %s: %s", company_id, e)
        return False


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


def create_contact(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new contact linked to a company. Returns the created record."""
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('contacts').insert(data).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error creating contact: %s", e)
        return None


def update_contact(contact_id: str, data: Dict[str, Any]) -> bool:
    """Update contact fields. Returns True on success."""
    client = _get_client()
    if not client:
        return False

    try:
        client.table('contacts').update(data).eq('id', contact_id).execute()
        return True

    except Exception as e:
        logger.warning("Error updating contact %s: %s", contact_id, e)
        return False


def find_contacts_by_company(company_id: str) -> List[Dict[str, Any]]:
    """Get all contacts for a company, primary contact first."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('contacts').select('*').eq(
            'company_id', company_id
        ).order('is_primary', desc=True).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error finding contacts for company %s: %s", company_id, e)
        return []


def get_contact_by_id(contact_id: str) -> Optional[Dict[str, Any]]:
    """Get a single contact by ID."""
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('contacts').select('*').eq('id', contact_id).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error fetching contact %s: %s", contact_id, e)
        return None


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------


def create_deal(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new deal. Returns the created record."""
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('deals').insert(data).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error creating deal: %s", e)
        return None


def update_deal(deal_id: str, data: Dict[str, Any]) -> bool:
    """
    Update deal fields (stage, value, next_action, notes, etc).

    Automatically sets closed_at when stage changes to closed_won or closed_lost.
    Returns True on success.
    """
    client = _get_client()
    if not client:
        return False

    try:
        if data.get('stage') in ('closed_won', 'closed_lost'):
            data['closed_at'] = datetime.now(timezone.utc).isoformat()
        client.table('deals').update(data).eq('id', deal_id).execute()
        return True

    except Exception as e:
        logger.warning("Error updating deal %s: %s", deal_id, e)
        return False


def get_deals_by_company(company_id: str) -> List[Dict[str, Any]]:
    """Get all deals for a company (most recent first)."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('deals').select('*').eq(
            'company_id', company_id
        ).order('created_at', desc=True).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching deals for company %s: %s", company_id, e)
        return []


def get_deals_by_stage(stage: str) -> List[Dict[str, Any]]:
    """Get all deals in a specific stage, with company and contact info."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('deals').select(
            '*, companies(company_name, company_url), contacts(name, title)'
        ).eq('stage', stage).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching deals by stage %s: %s", stage, e)
        return []


def get_active_deals() -> List[Dict[str, Any]]:
    """Get all non-closed deals, ordered by next_action_date."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('deals').select(
            '*, companies(company_name, company_url), contacts(name, title)'
        ).neq('stage', 'closed_won').neq('stage', 'closed_lost').order(
            'next_action_date'
        ).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching active deals: %s", e)
        return []


def get_overdue_deals() -> List[Dict[str, Any]]:
    """Get deals with next_action_date in the past (overdue follow-ups)."""
    client = _get_client()
    if not client:
        return []

    try:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        response = client.table('deals').select(
            '*, companies(company_name, company_url), contacts(name, title)'
        ).lte('next_action_date', today).neq(
            'stage', 'closed_won'
        ).neq('stage', 'closed_lost').order('next_action_date').execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching overdue deals: %s", e)
        return []


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


def log_activity(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Log a new activity (email, whatsapp, linkedin, meeting, call, note).

    Returns the created activity record.
    """
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('activities').insert(data).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error logging activity: %s", e)
        return None


def update_activity(activity_id: str, data: Dict[str, Any]) -> bool:
    """Update activity fields (status, meeting_summary, client_replies, etc)."""
    client = _get_client()
    if not client:
        return False

    try:
        client.table('activities').update(data).eq('id', activity_id).execute()
        return True

    except Exception as e:
        logger.warning("Error updating activity %s: %s", activity_id, e)
        return False


def get_activities_by_company(company_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get activity timeline for a company (most recent first)."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('activities').select(
            '*, contacts(name)'
        ).eq('company_id', company_id).order(
            'executed_at', desc=True
        ).limit(limit).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching activities for company %s: %s", company_id, e)
        return []


def get_activities_by_deal(deal_id: str) -> List[Dict[str, Any]]:
    """Get all activities for a specific deal."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('activities').select(
            '*, contacts(name)'
        ).eq('deal_id', deal_id).order('executed_at', desc=True).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching activities for deal %s: %s", deal_id, e)
        return []


def get_pending_followups(days_ahead: int = 3) -> List[Dict[str, Any]]:
    """Get activities with pending follow-ups within the next N days."""
    client = _get_client()
    if not client:
        return []

    try:
        cutoff = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()
        response = client.table('activities').select(
            '*, companies(company_name, company_url), contacts(name)'
        ).lte('next_followup_at', cutoff).order('next_followup_at').execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching pending followups: %s", e)
        return []


# ---------------------------------------------------------------------------
# Prospects — outbound prospect database
# ---------------------------------------------------------------------------


def upsert_prospect(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Insert or update a prospect by email (primary key).

    Expects: email, company_url, first_name, last_name, linkedin_url, job,
    description, status.
    """
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('prospects').upsert(
            data, on_conflict='email'
        ).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error upserting prospect: %s", e)
        return None


def get_prospect_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get a prospect by email."""
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('prospects').select('*').eq('email', email).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error fetching prospect %s: %s", email, e)
        return None


def get_prospects_by_company(company_url: str) -> List[Dict[str, Any]]:
    """Get all prospects for a company."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('prospects').select('*').eq(
            'company_url', company_url
        ).order('created_at', desc=True).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching prospects for %s: %s", company_url, e)
        return []


def update_prospect(email: str, data: Dict[str, Any]) -> bool:
    """Update prospect fields. Returns True on success."""
    client = _get_client()
    if not client:
        return False

    try:
        client.table('prospects').update(data).eq('email', email).execute()
        return True

    except Exception as e:
        logger.warning("Error updating prospect %s: %s", email, e)
        return False


# ---------------------------------------------------------------------------
# Prospects Demo — AEO visibility results per prospect
# ---------------------------------------------------------------------------


def upsert_prospect_demo(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Insert or update an AEO demo result.

    PK is (prospect_email, prompt, model). If a result for the same
    prospect/prompt/model combo exists, it gets updated.

    Expects: prospect_email, prompt, model, company_url,
    mentions_rate, ranking, share_of_voice, sentiment, citation_rate,
    overall_score, report (bytes — PDF file).
    """
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('prospects_demo').upsert(
            data, on_conflict='prospect_email,prompt,model'
        ).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error upserting prospect demo: %s", e)
        return None


def get_prospect_demos_by_company(company_url: str) -> List[Dict[str, Any]]:
    """Get all AEO demo results for a company (most recent first)."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('prospects_demo').select('*').eq(
            'company_url', company_url
        ).order('measured_at', desc=True).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching prospect demos for %s: %s", company_url, e)
        return []


def get_prospect_demos_by_model(company_url: str, model: str) -> List[Dict[str, Any]]:
    """Get AEO demo results for a company filtered by AI model."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('prospects_demo').select('*').eq(
            'company_url', company_url
        ).eq('model', model).order('measured_at', desc=True).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching prospect demos for %s model %s: %s", company_url, model, e)
        return []


def get_prospect_demo_by_email(prospect_email: str) -> Optional[Dict[str, Any]]:
    """Get AEO demo result for a specific prospect."""
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('prospects_demo').select('*').eq(
            'prospect_email', prospect_email
        ).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error fetching prospect demo for %s: %s", prospect_email, e)
        return None


def prospect_report_url(prospect_email: str) -> str:
    """
    Build a shareable landing page URL for a prospect's AEO reports,
    shortened via Bitly if BITLY_TOKEN is set.
    """
    base = os.getenv('SUPABASE_URL', '')
    full_url = f"{base}/functions/v1/prospect-reports?email={prospect_email}"

    bitly_token = os.getenv('BITLY_TOKEN')
    if not bitly_token:
        return full_url

    try:
        import requests as req
        resp = req.post(
            'https://api-ssl.bitly.com/v4/shorten',
            json={'long_url': full_url},
            headers={'Authorization': f'Bearer {bitly_token}'},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get('link', full_url)

    except Exception as e:
        logger.warning("Bitly shortening failed for %s: %s", prospect_email, e)
        return full_url


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


def create_campaign(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new outreach campaign. Returns the created record."""
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('campaigns').insert(data).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error creating campaign: %s", e)
        return None


def update_campaign(campaign_id: str, data: Dict[str, Any]) -> bool:
    """Update campaign fields (status, stats, description)."""
    client = _get_client()
    if not client:
        return False

    try:
        client.table('campaigns').update(data).eq('id', campaign_id).execute()
        return True

    except Exception as e:
        logger.warning("Error updating campaign %s: %s", campaign_id, e)
        return False


def get_campaigns_by_status(status: str) -> List[Dict[str, Any]]:
    """Get campaigns by status (draft, active, paused, completed)."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('campaigns').select('*').eq(
            'status', status
        ).order('created_at', desc=True).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching campaigns by status %s: %s", status, e)
        return []


# ---------------------------------------------------------------------------
# Campaign Contacts
# ---------------------------------------------------------------------------


def enroll_contact_in_campaign(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Enroll a contact in a campaign.

    Expects: campaign_id, contact_id, company_id, message_body (optional).
    Returns the enrollment record.
    """
    client = _get_client()
    if not client:
        return None

    try:
        response = client.table('campaign_contacts').insert(data).execute()
        return response.data[0] if response.data else None

    except Exception as e:
        logger.warning("Error enrolling contact in campaign: %s", e)
        return None


def update_campaign_contact(enrollment_id: str, data: Dict[str, Any]) -> bool:
    """
    Update campaign contact status (sent, delivered, opened, replied, etc).

    Automatically sets timestamps: sent_at, opened_at, replied_at based on status.
    """
    client = _get_client()
    if not client:
        return False

    try:
        now = datetime.now(timezone.utc).isoformat()
        status = data.get('status')
        if status == 'sent' and 'sent_at' not in data:
            data['sent_at'] = now
        elif status == 'opened' and 'opened_at' not in data:
            data['opened_at'] = now
        elif status == 'replied' and 'replied_at' not in data:
            data['replied_at'] = now

        client.table('campaign_contacts').update(data).eq('id', enrollment_id).execute()
        return True

    except Exception as e:
        logger.warning("Error updating campaign contact %s: %s", enrollment_id, e)
        return False


def get_campaign_contacts(campaign_id: str) -> List[Dict[str, Any]]:
    """Get all contacts enrolled in a campaign with their status."""
    client = _get_client()
    if not client:
        return []

    try:
        response = client.table('campaign_contacts').select(
            '*, contacts(name, title, email), companies(company_name, company_url)'
        ).eq('campaign_id', campaign_id).execute()
        return response.data or []

    except Exception as e:
        logger.warning("Error fetching campaign contacts for %s: %s", campaign_id, e)
        return []


def get_campaign_stats(campaign_id: str) -> Dict[str, int]:
    """
    Compute live campaign stats from campaign_contacts rows.

    Returns dict with: total, sent, delivered, opened, replied, bounced, opted_out.
    """
    client = _get_client()
    if not client:
        return {}

    try:
        response = client.table('campaign_contacts').select(
            'status'
        ).eq('campaign_id', campaign_id).execute()

        rows = response.data or []
        stats = {
            'total': len(rows),
            'sent': 0, 'delivered': 0, 'opened': 0,
            'replied': 0, 'bounced': 0, 'opted_out': 0,
        }
        for row in rows:
            s = row.get('status', '')
            if s in stats:
                stats[s] += 1
        return stats

    except Exception as e:
        logger.warning("Error computing campaign stats for %s: %s", campaign_id, e)
        return {}
