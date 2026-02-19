"""
Seed Supabase prospects table with initial data.

Run after creating the table with config/supabase_schema.sql.

Usage:
    uv run python products/b2b_outreach/claude/seed_supabase.py
"""

import logging
import os
import sys

from supabase import create_client

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

PROSPECTS = [
    {
        'company_name': 'Falabella',
        'company_url': 'falabella.com',
        'company_description': (
            'Falabella es uno de los mayores conglomerados de retail de América Latina, '
            'con presencia en Chile, Perú, Colombia y Argentina. Opera tiendas por departamento, '
            'tiendas de mejoramiento del hogar (Sodimac), supermercados (Tottus), '
            'marketplace online (falabella.com) y servicios financieros (Banco Falabella).'
        ),
        'person_name': 'María González',        # Replace with real contact name
        'person_job': 'Gerente de Marketing Digital',
        'person_phone': None,                   # Replace with real phone
        'person_email': None,                   # Replace with real email
        'person_description': (
            'Lidera la estrategia de marketing digital de Falabella Chile, '
            'con foco en SEO, medios pagados y tecnología de marketing.'
        ),
    },
]


def seed():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        sys.exit(1)

    client = create_client(url, key)

    for prospect in PROSPECTS:
        domain = prospect['company_url']
        existing = client.table('prospects').select('id').eq('company_url', domain).execute()
        if existing.data:
            logger.info(
                "Prospect for %s already exists (id: %s) — skipping",
                domain, existing.data[0]['id']
            )
            continue

        response = client.table('prospects').insert(prospect).execute()
        inserted = response.data[0] if response.data else {}
        logger.info(
            "Inserted prospect: %s / %s (id: %s)",
            prospect['company_name'], prospect['person_name'], inserted.get('id')
        )


if __name__ == '__main__':
    seed()
