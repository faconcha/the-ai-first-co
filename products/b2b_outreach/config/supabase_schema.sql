-- ============================================================================
-- B2B Outreach CRM Schema
-- ============================================================================
-- 8 tables: companies, contacts, deals, activities, prospects, prospects_demo,
-- campaigns, campaign_contacts. Plus views for pipeline overview, follow-ups, and
-- campaign performance.
--
-- Run in the Supabase SQL editor (or via apply_migration MCP).
-- ============================================================================


-- Utility: auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- 1. COMPANIES — Company profile only (no pipeline data)
-- ============================================================================

CREATE TABLE IF NOT EXISTS companies (
    company_url         TEXT NOT NULL PRIMARY KEY,  -- e.g. falabella.com
    id                  UUID DEFAULT gen_random_uuid() UNIQUE,
    company_name        TEXT NOT NULL,
    industry            TEXT,
    country             TEXT,                      -- ISO code (CL, MX, US)
    city                TEXT,
    description         TEXT,
    annual_revenue      TEXT,
    employee_count      TEXT,
    competitors         JSONB DEFAULT '[]'::jsonb,  -- [{"aliases": [...], "website_url": "..."}]

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_industry        ON companies (industry);

DROP TRIGGER IF EXISTS trg_companies_updated_at ON companies;
CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================================
-- 2. CONTACTS — People database, linked to companies
-- ============================================================================

CREATE TABLE IF NOT EXISTS contacts (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    name            TEXT NOT NULL,
    title           TEXT,                          -- "Gerente de Marketing Digital"
    role            TEXT CHECK (role IN (
                        'decision_maker',          -- CMO, CEO, VP
                        'influencer',              -- Manager, director who recommends
                        'champion',                -- Internal advocate
                        'user',                    -- End user of the product
                        'gatekeeper',              -- Controls access (secretary, assistant)
                        'unknown'
                    )) DEFAULT 'unknown',
    email           TEXT,
    phone           TEXT,
    linkedin_url    TEXT,

    -- Source tracking
    source          TEXT NOT NULL CHECK (source IN (
                        'outbound_db',             -- Imported from a database/CSV
                        'inbound_form',            -- User filled your web form
                        'linkedin',                -- Found/connected on LinkedIn
                        'referral',                -- Introduced by someone
                        'event',                   -- Met at conference/event
                        'cold_outreach',           -- Found via research
                        'other'
                    )),

    -- Inbound form responses (for source = 'inbound_form')
    form_responses  JSONB,

    is_primary      BOOLEAN DEFAULT FALSE,
    notes           TEXT,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts (company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_source  ON contacts (source);
CREATE INDEX IF NOT EXISTS idx_contacts_role    ON contacts (role);

DROP TRIGGER IF EXISTS trg_contacts_updated_at ON contacts;
CREATE TRIGGER trg_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================================
-- 3. DEALS — Sales pipeline
-- ============================================================================

CREATE TABLE IF NOT EXISTS deals (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    primary_contact_id  UUID REFERENCES contacts(id) ON DELETE SET NULL,

    stage               TEXT NOT NULL DEFAULT 'prospecting' CHECK (stage IN (
                            'prospecting',         -- Initial research, not contacted yet
                            'contacted',           -- First outreach sent
                            'qualified',           -- Confirmed fit, interest shown
                            'demo_scheduled',      -- Demo meeting booked
                            'demo_done',           -- Demo completed
                            'proposal_sent',       -- Commercial proposal delivered
                            'negotiation',         -- Active negotiation
                            'closed_won',          -- Deal closed successfully
                            'closed_lost'          -- Deal lost
                        )),

    value               REAL,                      -- Estimated deal value
    currency            TEXT DEFAULT 'USD',
    lost_reason         TEXT,                      -- Only for closed_lost

    -- Follow-up management
    next_action         TEXT,                      -- "Send proposal", "Follow up on demo"
    next_action_date    DATE,

    notes               TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    closed_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_deals_company     ON deals (company_id);
CREATE INDEX IF NOT EXISTS idx_deals_stage       ON deals (stage);
CREATE INDEX IF NOT EXISTS idx_deals_next_action ON deals (next_action_date)
    WHERE next_action_date IS NOT NULL;

DROP TRIGGER IF EXISTS trg_deals_updated_at ON deals;
CREATE TRIGGER trg_deals_updated_at
    BEFORE UPDATE ON deals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================================
-- 4. ACTIVITIES — Every touchpoint (CRM core)
-- ============================================================================

CREATE TABLE IF NOT EXISTS activities (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    deal_id         UUID REFERENCES deals(id) ON DELETE SET NULL,
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    contact_id      UUID REFERENCES contacts(id) ON DELETE SET NULL,

    channel         TEXT NOT NULL CHECK (channel IN (
                        'email',
                        'whatsapp',
                        'linkedin_message',
                        'linkedin_connection',
                        'phone_call',
                        'meeting',
                        'note'
                    )),
    direction       TEXT CHECK (direction IN ('outbound', 'inbound')),

    -- Content
    subject         TEXT,                          -- Email subject or meeting topic
    body            TEXT,                          -- Message content or meeting notes

    -- Meeting-specific fields
    meeting_summary     TEXT,                      -- What was discussed
    client_objections   TEXT,                      -- Objections raised
    client_replies      TEXT,                      -- Key things the client said
    agreed_next_steps   TEXT,                      -- What was agreed

    -- Status
    status          TEXT DEFAULT 'sent' CHECK (status IN (
                        'scheduled',               -- Future meeting or send
                        'sent',                    -- Message sent
                        'delivered',               -- Confirmed delivered
                        'opened',                  -- Email opened / WhatsApp read
                        'replied',                 -- Client responded
                        'bounced',                 -- Failed delivery
                        'completed',               -- Meeting completed
                        'no_show',                 -- Meeting, contact didn't show
                        'cancelled'
                    )),

    -- Timing
    scheduled_at     TIMESTAMPTZ,                  -- When it's scheduled to happen
    executed_at      TIMESTAMPTZ DEFAULT NOW(),     -- When it actually happened
    next_followup_at TIMESTAMPTZ,                  -- When to follow up after this

    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activities_deal     ON activities (deal_id);
CREATE INDEX IF NOT EXISTS idx_activities_company  ON activities (company_id);
CREATE INDEX IF NOT EXISTS idx_activities_contact  ON activities (contact_id);
CREATE INDEX IF NOT EXISTS idx_activities_channel  ON activities (channel);
CREATE INDEX IF NOT EXISTS idx_activities_followup ON activities (next_followup_at)
    WHERE next_followup_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_activities_timeline ON activities (company_id, executed_at DESC);


-- ============================================================================
-- 5. PROSPECTS — People database for outbound outreach
-- ============================================================================

CREATE TABLE IF NOT EXISTS prospects (
    email           TEXT NOT NULL PRIMARY KEY,
    company_url     TEXT NOT NULL REFERENCES companies(company_url) ON DELETE CASCADE,
    first_name      TEXT,
    last_name       TEXT,
    linkedin_url    TEXT,
    job             TEXT,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
                        'active', 'inactive'
                    )),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prospects_company ON prospects (company_url);
CREATE INDEX IF NOT EXISTS idx_prospects_status  ON prospects (status);

DROP TRIGGER IF EXISTS trg_prospects_updated_at ON prospects;
CREATE TRIGGER trg_prospects_updated_at
    BEFORE UPDATE ON prospects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================================
-- 6. PROSPECTS_DEMO — AEO visibility results per prospect
-- ============================================================================

CREATE TABLE IF NOT EXISTS prospects_demo (
    -- Composite PK: one result per (prospect, prompt, model)
    prospect_email  TEXT NOT NULL REFERENCES prospects(email) ON DELETE CASCADE,
    prompt          TEXT NOT NULL,                  -- the search query tested
    model           TEXT NOT NULL,                  -- AI model (chatgpt, claude, gemini, etc.)
    PRIMARY KEY (prospect_email, prompt, model),

    company_url     TEXT NOT NULL REFERENCES companies(company_url) ON DELETE CASCADE,

    -- AEO KPIs
    mentions_rate   REAL,                          -- how often the company is mentioned
    ranking         REAL,                          -- position in AI recommendations
    share_of_voice  REAL,                          -- share vs. competitors
    sentiment       REAL,                          -- positive/negative tone
    citation_rate   REAL,                          -- how often sources are cited
    overall_score   REAL,                          -- composite AEO score

    -- Report (PDF binary)
    report          BYTEA,                         -- PDF report file

    measured_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prospects_demo_url    ON prospects_demo (company_url);
CREATE INDEX IF NOT EXISTS idx_prospects_demo_email  ON prospects_demo (prospect_email);
CREATE INDEX IF NOT EXISTS idx_prospects_demo_latest ON prospects_demo (company_url, measured_at DESC);

DROP TRIGGER IF EXISTS trg_prospects_demo_updated_at ON prospects_demo;
CREATE TRIGGER trg_prospects_demo_updated_at
    BEFORE UPDATE ON prospects_demo
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================================
-- 7. CAMPAIGNS — Outreach campaign definitions
-- ============================================================================

CREATE TABLE IF NOT EXISTS campaigns (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name            TEXT NOT NULL,                 -- "LATAM Retailers Q1 2026"
    channel         TEXT NOT NULL CHECK (channel IN (
                        'email', 'whatsapp', 'linkedin', 'multi_channel'
                    )),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
                        'draft',                   -- Being prepared
                        'active',                  -- Currently running
                        'paused',                  -- Temporarily stopped
                        'completed'                -- Finished
                    )),
    description     TEXT,

    -- Denormalized stats (updated by application code)
    total_enrolled  INTEGER DEFAULT 0,
    total_sent      INTEGER DEFAULT 0,
    total_opened    INTEGER DEFAULT 0,
    total_replied   INTEGER DEFAULT 0,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns (status);

DROP TRIGGER IF EXISTS trg_campaigns_updated_at ON campaigns;
CREATE TRIGGER trg_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================================
-- 8. CAMPAIGN_CONTACTS — Per-contact enrollment + message tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS campaign_contacts (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    contact_id      UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Message tracking
    message_body    TEXT,                          -- The actual message sent
    status          TEXT NOT NULL DEFAULT 'enrolled' CHECK (status IN (
                        'enrolled',                -- Added to campaign, not yet sent
                        'sent',                    -- Message sent
                        'delivered',               -- Confirmed delivered
                        'opened',                  -- Opened/read
                        'replied',                 -- Got a response
                        'bounced',                 -- Failed delivery
                        'opted_out'                -- Contact asked to stop
                    )),

    sent_at         TIMESTAMPTZ,
    opened_at       TIMESTAMPTZ,
    replied_at      TIMESTAMPTZ,
    reply_content   TEXT,                          -- What the contact replied

    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(campaign_id, contact_id)                -- One enrollment per contact per campaign
);

CREATE INDEX IF NOT EXISTS idx_cc_campaign ON campaign_contacts (campaign_id);
CREATE INDEX IF NOT EXISTS idx_cc_contact  ON campaign_contacts (contact_id);
CREATE INDEX IF NOT EXISTS idx_cc_status   ON campaign_contacts (campaign_id, status);


-- ============================================================================
-- VIEWS
-- ============================================================================

-- Pipeline overview: companies with their active deal and last activity
CREATE OR REPLACE VIEW pipeline_overview AS
SELECT
    comp.id             AS company_id,
    comp.company_name,
    comp.company_url,
    comp.industry,
    d.id                AS deal_id,
    d.stage,
    d.value,
    d.currency,
    d.next_action,
    d.next_action_date,
    ct.name             AS contact_name,
    ct.title            AS contact_title,
    ct.email            AS contact_email,
    (SELECT MAX(a.executed_at) FROM activities a WHERE a.company_id = comp.id) AS last_activity_at,
    (SELECT COUNT(*)            FROM activities a WHERE a.company_id = comp.id) AS total_activities
FROM companies comp
LEFT JOIN deals d     ON d.company_id = comp.id AND d.stage NOT IN ('closed_won', 'closed_lost')
LEFT JOIN contacts ct ON ct.id = d.primary_contact_id;


-- Follow-ups due in the next 3 days (from both deals and activities)
CREATE OR REPLACE VIEW pending_followups AS
SELECT source, id, company_id, company_name, contact_name, channel, due_date, context
FROM (
    SELECT
        'deal'::TEXT            AS source,
        d.id,
        d.company_id,
        comp.company_name       AS company_name,
        ct.name                 AS contact_name,
        d.stage                 AS channel,
        d.next_action_date::TIMESTAMPTZ AS due_date,
        d.next_action           AS context
    FROM deals d
    JOIN companies comp ON comp.id = d.company_id
    LEFT JOIN contacts ct ON ct.id = d.primary_contact_id
    WHERE d.next_action_date IS NOT NULL
      AND d.next_action_date <= CURRENT_DATE + INTERVAL '3 days'
      AND d.stage NOT IN ('closed_won', 'closed_lost')
    UNION ALL
    SELECT
        'activity'::TEXT        AS source,
        a.id,
        a.company_id,
        comp.company_name       AS company_name,
        ct.name                 AS contact_name,
        a.channel,
        a.next_followup_at      AS due_date,
        a.body                  AS context
    FROM activities a
    JOIN companies comp ON comp.id = a.company_id
    LEFT JOIN contacts ct ON ct.id = a.contact_id
    WHERE a.next_followup_at IS NOT NULL
      AND a.next_followup_at <= NOW() + INTERVAL '3 days'
) sub
ORDER BY due_date;


-- Campaign performance summary
CREATE OR REPLACE VIEW campaign_performance AS
SELECT
    camp.id,
    camp.name,
    camp.channel,
    camp.status,
    camp.total_enrolled,
    camp.total_sent,
    camp.total_opened,
    camp.total_replied,
    CASE WHEN camp.total_sent > 0
         THEN ROUND(camp.total_opened::NUMERIC / camp.total_sent * 100, 1)
         ELSE 0
    END AS open_rate,
    CASE WHEN camp.total_sent > 0
         THEN ROUND(camp.total_replied::NUMERIC / camp.total_sent * 100, 1)
         ELSE 0
    END AS reply_rate,
    camp.created_at,
    camp.updated_at
FROM campaigns camp;


