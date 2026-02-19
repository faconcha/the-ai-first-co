-- B2B Outreach: prospects table
-- Run this in the Supabase SQL editor to set up the schema.

CREATE TABLE IF NOT EXISTS prospects (
    id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_name         TEXT NOT NULL,
    company_url          TEXT NOT NULL,          -- company domain, e.g. "falabella.com"
    company_description  TEXT,
    person_name          TEXT NOT NULL,
    person_job           TEXT,                   -- job title, used to infer role (CMO, CEO, etc.)
    person_phone         TEXT,
    person_email         TEXT,
    person_description   TEXT,
    signals              JSONB,                  -- latest signal detection result (from run_pipeline)
    signals_detected_at  TIMESTAMPTZ,            -- when signals were last detected
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast company lookups (domain-first, then name fallback)
CREATE INDEX IF NOT EXISTS idx_prospects_company_url  ON prospects (company_url);
CREATE INDEX IF NOT EXISTS idx_prospects_company_name ON prospects (lower(company_name));
