---
name: research-company
description: Deep B2B sales research on a company for the outreach pipeline
argument-hint: <company_name> <domain> [industry]
allowed-tools:
  - WebSearch
  - WebFetch
  - Read
  - Glob
  - Write
  - Bash(uv run python:*)
---

Research the company specified in $ARGUMENTS for B2B outbound sales. Your goal is to build the most complete prospect profile possible — the kind of intelligence a top salesperson would want before making a call.

## Parse Arguments

Extract from $ARGUMENTS:
- `company_name`: first argument (required)
- `domain`: second argument (required)
- `industry`: third argument (optional, default "Unknown")

## Step 1: Determine Output Path

Read `products/b2b_outreach/config/b2b_outreach.yaml` and extract `output.base_path` and `output.folder_pattern`. Compute the output directory:
```
{base_path}/{folder_pattern with company_name=<company_slug>}/
```
where `company_slug` = company_name lowercased with spaces replaced by underscores.

Create the output directory if it doesn't exist.

## Step 2: Web Search (be exhaustive)

Use `WebSearch` to gather intelligence. Run ALL of these searches:

1. `"{company_name}" company overview products services subsidiaries` — general profile
2. `"{company_name}" competitors market position industry` — competitive landscape
3. `"{company_name}" {domain} news announcements 2025 2026` — recent activity
4. `"{company_name}" digital transformation technology strategy AI` — tech priorities
5. `"{company_name}" revenue employees company size` — financial profile
6. `"{company_name}" challenges problems risks` — company pain points

Run them in parallel for speed. Read every result carefully.

## Step 3: Website Fetch

Use `WebFetch` to extract content from these pages on the company domain:
- `https://{domain}/` — homepage
- `https://{domain}/about` or `/nosotros` or `/quienes-somos` — about page
- `https://{domain}/products` or `/productos` or `/servicios` — products/services

For each page, use the prompt: "Extract everything relevant for a B2B salesperson: products, services, value proposition, target audience, partners, technology mentions, and strategic messaging."

If a page fails or redirects, skip it and continue.

## Step 4: Synthesize

Think like a B2B salesperson preparing for the most important call of the quarter. Combine web search results, website content, AND your own knowledge about the company.

Produce a JSON object with this exact structure:

```json
{
  "name": "<official company name>",
  "domain": "<domain>",
  "industry": "<primary industry>",
  "products": ["<actual product/brand names>"],
  "services": ["<actual service offerings>"],
  "value_proposition": "<1-2 sentence core value proposition>",
  "target_audience": "<who they sell to>",
  "pain_points": ["<problems the company solves for ITS customers>"],
  "country": "<ISO 2-letter code>",
  "city": "<HQ city or null>",
  "aliases": ["<subsidiary brands, trade names, related domains>"],
  "competitors": ["<real competitor company names>"],
  "business_context": [
    "<revenue, EBITDA, margins, growth rate>",
    "<investment plans, capex, expansion>",
    "<store/office count, geographic reach>",
    "<recent announcements, M&A, partnerships>",
    "<market position, market share>"
  ],
  "strategic_priorities": [
    "<what they are investing in right now>",
    "<digital transformation initiatives>",
    "<geographic or product expansion plans>",
    "<AI, automation, or tech modernization efforts>"
  ],
  "company_challenges": [
    "<their OWN operational challenges, NOT their customers' problems>",
    "<competitive threats they face>",
    "<market pressures, regulatory issues>",
    "<technology gaps or legacy system problems>",
    "<talent, supply chain, or margin pressures>"
  ],
  "tech_stack": [
    "<known platforms: e-commerce engine, CRM, ERP, cloud provider>",
    "<marketing tools, analytics platforms>",
    "<any technology partnerships or vendor relationships>"
  ],
  "buying_triggers": [
    "<recent events creating purchase opportunities>",
    "<new leadership, reorg, or mandate changes>",
    "<expansion into new markets or channels>",
    "<technology budget increases>",
    "<competitive pressure forcing action>"
  ],
  "annual_revenue": "<e.g. 'US$13B'>",
  "employee_count": "<e.g. '100,000+'>"
}
```

### Field rules

- `products`: Actual product/brand names, not generic categories. Include subsidiary brands.
- `services`: Real service offerings (banking, logistics, insurance, etc.), not vague descriptions.
- `pain_points`: What problems the company solves for ITS CUSTOMERS. Used downstream to generate discovery prompts.
- `aliases`: Every subsidiary brand, trade name, and related domain you can find.
- `competitors`: Real company names only. Include both direct and indirect competitors.
- `business_context`: Hard numbers — revenue, growth %, margins, investment figures, store counts. Be specific with figures and dates.
- `strategic_priorities`: What the company is actively investing in or publicly committed to. These are hooks for your sales pitch.
- `company_challenges`: The company's OWN problems — competitive threats, margin pressure, tech debt, talent gaps, regulatory risk. This is gold for a salesperson: if you can solve one of these, you have a meeting.
- `tech_stack`: Any technology, platform, or vendor they use. Check job postings, press releases, and tech blogs for clues.
- `buying_triggers`: Recent events that create urgency — new funding, leadership change, expansion, digital transformation mandate, competitive loss. The more recent, the better.
- `annual_revenue` and `employee_count`: Best available estimates. Use ranges if exact figures aren't public.

### Quality checklist

Before saving, verify:
- [ ] No field is empty or null if you can reasonably fill it
- [ ] `business_context` has at least 3 items with real numbers
- [ ] `strategic_priorities` reflects what the company is CURRENTLY focused on
- [ ] `company_challenges` lists problems THEY face, not their customers
- [ ] `competitors` has at least 3 real companies
- [ ] `buying_triggers` lists at least 2 recent events

## Step 5: Save

Write the JSON to `{output_dir}/01_research.json` using the Write tool.

Show the user a summary:
- Company name, industry, HQ, revenue, employee count
- Number of products, services, competitors, and decision makers found
- Top 3 buying triggers (the salesperson cares about these most)
- Top 3 company challenges (these are conversation openers)
