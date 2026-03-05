"""
Seed Supabase CRM tables with sample data.

Creates sample companies, contacts, and deals for testing the CRM schema.
Run after applying the migration in config/supabase_schema.sql.

Usage:
    uv run python products/b2b_outreach/claude/seed_supabase.py
"""

import logging
import os
import sys

from supabase import create_client

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

COMPANIES = [
    {
        'company_name': 'Falabella',
        'company_url': 'falabella.com',
        'industry': 'Retail',
        'country': 'CL',
        'city': 'Santiago',
        'description': (
            'Falabella es uno de los mayores conglomerados de retail de América Latina, '
            'con presencia en Chile, Perú, Colombia y Argentina. Opera tiendas por departamento, '
            'tiendas de mejoramiento del hogar (Sodimac), supermercados (Tottus), '
            'marketplace online (falabella.com) y servicios financieros (Banco Falabella).'
        ),
    },
    {
        'company_name': 'Rappi',
        'company_url': 'rappi.com',
        'industry': 'Delivery / Marketplace',
        'country': 'CO',
        'city': 'Bogotá',
        'description': (
            'Rappi es una superapp de delivery y servicios on-demand líder en América Latina. '
            'Opera en 9 países con servicios de comida, supermercado, farmacia, pagos y envíos.'
        ),
    },
]

CONTACTS = [
    {
        'company_url': 'falabella.com',
        'name': 'María González',
        'title': 'Gerente de Marketing Digital',
        'role': 'decision_maker',
        'source': 'outbound_db',
        'is_primary': True,
    },
    {
        'company_url': 'falabella.com',
        'name': 'Carlos Muñoz',
        'title': 'Jefe de SEO y Performance',
        'role': 'influencer',
        'source': 'linkedin',
        'is_primary': False,
    },
    {
        'company_url': 'rappi.com',
        'name': 'Andrea López',
        'title': 'VP Marketing',
        'role': 'decision_maker',
        'source': 'cold_outreach',
        'is_primary': True,
    },
]

DEALS = [
    {
        'company_url': 'falabella.com',
        'stage': 'demo_scheduled',
        'value': 5000.0,
        'currency': 'USD',
        'next_action': 'Preparar demo personalizada con datos de visibilidad',
        'next_action_date': '2026-02-25',
    },
    {
        'company_url': 'rappi.com',
        'stage': 'prospecting',
        'value': 3000.0,
        'currency': 'USD',
        'next_action': 'Enviar mensaje por LinkedIn',
    },
]


def seed():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        sys.exit(1)

    client = create_client(url, key)

    # Seed companies
    company_ids = {}
    for company in COMPANIES:
        url = company['company_url']
        existing = client.table('companies').select('id').eq('company_url', url).execute()
        if existing.data:
            company_ids[url] = existing.data[0]['id']
            logger.info("Company %s already exists (id: %s) — skipping",
                        url, existing.data[0]['id'])
            continue

        response = client.table('companies').insert(company).execute()
        inserted = response.data[0] if response.data else {}
        company_ids[url] = inserted.get('id')
        logger.info("Inserted company: %s (id: %s)", company['company_name'], inserted.get('id'))

    # Seed contacts
    for contact in CONTACTS:
        url = contact.pop('company_url')
        company_id = company_ids.get(url)
        if not company_id:
            logger.warning("No company found for %s — skipping contact %s", url, contact['name'])
            contact['company_url'] = url
            continue

        contact['company_id'] = company_id
        existing = client.table('contacts').select('id').eq(
            'company_id', company_id
        ).eq('name', contact['name']).execute()

        if existing.data:
            logger.info("Contact %s already exists — skipping", contact['name'])
            contact['company_url'] = url
            continue

        response = client.table('contacts').insert(contact).execute()
        inserted = response.data[0] if response.data else {}
        logger.info("Inserted contact: %s for %s (id: %s)",
                    contact['name'], url, inserted.get('id'))
        contact['company_url'] = url

    # Seed deals
    for deal in DEALS:
        url = deal.pop('company_url')
        company_id = company_ids.get(url)
        if not company_id:
            deal['company_url'] = url
            continue

        deal['company_id'] = company_id

        # Link to primary contact
        primary = client.table('contacts').select('id').eq(
            'company_id', company_id
        ).eq('is_primary', True).execute()
        if primary.data:
            deal['primary_contact_id'] = primary.data[0]['id']

        existing = client.table('deals').select('id').eq(
            'company_id', company_id
        ).eq('stage', deal['stage']).execute()

        if existing.data:
            logger.info("Deal for %s in stage %s already exists — skipping", url, deal['stage'])
            deal['company_url'] = url
            continue

        response = client.table('deals').insert(deal).execute()
        inserted = response.data[0] if response.data else {}
        logger.info("Inserted deal: %s / %s (id: %s)", url, deal['stage'], inserted.get('id'))
        deal['company_url'] = url


if __name__ == '__main__':
    seed()
