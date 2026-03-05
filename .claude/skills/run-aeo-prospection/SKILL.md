---
name: run-aeo-prospection
description: Run the AEO full-pipeline for a prospect by email, fetching data from Supabase and calling the AEO endpoint
argument-hint: <prospect_email> [prompt1] [prompt2] ...
allowed-tools:
  - Bash(uv run python:*)
  - Read
  - Glob
  - WebSearch
---

Run the AEO prospection pipeline for the prospect specified in $ARGUMENTS.

## Parse Arguments

Extract from $ARGUMENTS:
- `prospect_email`: first argument (required)
- `prompts`: all remaining arguments (optional)

## Step 1: Fetch Prospect and Company Data

Run the pipeline script without prompts to fetch the data:
```bash
uv run python products/aeo_prospection/claude/run_prospection.py --email "<prospect_email>"
```

If the result contains `"error": "Prospect not found"`, tell the user and stop.
If the result contains `"error": "Company not found"`, tell the user and stop.

The script returns the prospect and company data when no prompts are provided.

## Step 2: Generate Prompts (if not provided)

If the user provided prompts in $ARGUMENTS, skip to Step 3.

Otherwise, use the company data returned in Step 1 (company_name, industry, description, country, city) to generate exactly 3 discovery prompts.

Rules for prompt generation:
- Write prompts in Spanish (unless the company country is US, UK, or another English-speaking country)
- Each prompt should be a natural question a buyer would ask an AI assistant (ChatGPT, Perplexity)
- Prompts should relate to the company's industry and services
- Prompts should be specific enough to potentially surface the company in AI responses
- Do NOT mention the company name in the prompts
- Include geographic context (city, country) when available

Example for a waste management company in Chile:
- "Que empresas me pueden ayudar con la gestion de residuos en la region de los lagos?"
- "Cuales son las mejores opciones para reciclaje industrial en el sur de Chile?"
- "Que empresas ofrecen servicios de educacion ambiental en Puerto Montt?"

## Step 3: Call the AEO Endpoint

Run the full pipeline with prompts (user-provided or generated):
```bash
uv run python products/aeo_prospection/claude/run_prospection.py --email "<prospect_email>" --prompts "<prompt1>" "<prompt2>" "<prompt3>"
```

This call may take 2-5 minutes. Wait for it to complete.

## Step 4: Display Results

Show the user a summary:
- Prospect name and company
- Number of prompts analyzed
- Models used
- Status (success/error)
- Supabase rows inserted
- Any errors from the endpoint

Format as a clear structured output.
