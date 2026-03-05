"""
LLM prompt templates for product discovery prompt generation.
"""


DISCOVERY_PROMPT_TEMPLATE = """You are a potential customer researching solutions in the {industry} space.

Company Context (DO NOT mention this company by name in any query):
- Industry: {industry}
- Products: {products}
- Services: {services}
- Value Proposition: {value_proposition}
- Target Audience: {target_audience}
- Pain Points they solve: {pain_points}

Task:
Generate exactly {n_prompts} realistic questions that a potential buyer would ask an AI assistant (ChatGPT, Claude, Gemini) when looking for a product or service like the ones this company offers.

Language: {language_instruction}

Requirements:
- Questions must sound like a real human talking to an AI assistant — natural, conversational, specific
- Each question should describe a real need or situation, not just keywords
- Focus ONLY on product/service discovery: "I need something that does X", "What's the best way to Y for my Z"
- Questions should reveal buying intent — the person is actively looking for a solution
- Do NOT include the company name in any query
- Do NOT write keyword-style queries like "best CRM tool" or "email marketing automation"
- Each question should be 10-25 words, like a sentence someone would type into ChatGPT

Good examples of the style:
- "I run a mid-size e-commerce store and need help optimizing my product pages for search, what tools exist?"
- "We're a SaaS company spending a lot on Google Ads but not showing up in AI search results, who can help?"
- "What's the best way for a restaurant chain to get recommended by AI assistants when people ask for dining options?"

Bad examples (DO NOT generate these):
- "best SEO tools 2024" (keyword-style, not conversational)
- "how to improve marketing" (too vague, no context)
- "Stripe alternatives for payments" (mentions a brand)

Output Format:
Return a JSON object with a single key "prompts" containing an array of exactly {n_prompts} strings.

Generate exactly {n_prompts} questions now:"""
