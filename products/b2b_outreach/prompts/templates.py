"""
LLM prompt templates for product discovery prompt generation.
"""


DISCOVERY_PROMPT_TEMPLATE = """You are a B2B marketing expert tasked with generating realistic search queries.

Company Context:
- Name: {company_name}
- Industry: {industry}
- Products: {products}
- Services: {services}
- Value Proposition: {value_proposition}
- Target Audience: {target_audience}
- Pain Points: {pain_points}

Task:
Generate {n_prompts} realistic search queries that a potential customer would use when discovering solutions like this company offers.

Language: {language_instruction}

Query Types to Include:
1. Product Discovery: "best [category] for [use_case]"
2. Problem-Solving: "how to [solve_pain_point]"
3. Vendor Comparison: "[competitor] alternatives"
4. Best Practices: "[industry] best practices for [goal]"
5. Feature Searches: "[specific_feature] tools"

Requirements:
- Queries must feel natural (how humans actually search in that language)
- Mix short (2-4 words) and long-tail (5-10 words) queries
- Include both generic and specific product categories
- Focus on user intent, not brand names
- Vary the query structures and topics
- Do NOT include the company name in the queries (we are testing if they appear organically)

Output Format:
Return a JSON object with a single key "prompts" containing an array of exactly {n_prompts} strings.

Example:
{{
  "prompts": [
    "best CRM for small business",
    "how to automate sales follow-up",
    "HubSpot alternatives for startups",
    "lead generation best practices B2B",
    "email marketing automation tools"
  ]
}}

Generate exactly {n_prompts} queries now:"""
