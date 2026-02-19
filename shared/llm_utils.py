"""
LLM Utilities
=============

Direct LLM query interface using Google GenAI (Gemini) and Anthropic SDKs.
Use this for prompt->response calls outside of CrewAI agent workflows.

Supported providers:
    - "gemini": Google GenAI (default)
    - "anthropic": Anthropic Claude

Provider is determined by the `provider` field in each profile (config/llm.yaml).
"""

import os
import json
import logging

from google import genai
import anthropic
from pydantic import BaseModel

from shared import settings

logger = logging.getLogger(__name__)

_gemini_client = None
_anthropic_client = None


def _ensure_gemini():
    """Create the Gemini client (once)."""
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _ensure_anthropic():
    """Create the Anthropic client (once)."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def _query_gemini(prompt, model, temperature, max_tokens):
    """Send a prompt to Gemini and return the response text."""
    client = _ensure_gemini()

    config = {"temperature": temperature}
    if max_tokens is not None:
        config["max_output_tokens"] = max_tokens

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return response.text


def _query_anthropic(prompt, model, temperature, max_tokens):
    """Send a prompt to Anthropic Claude and return the response text."""
    client = _ensure_anthropic()

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens or 4096,
    }

    response = client.messages.create(**kwargs)
    return response.content[0].text


def _query_gemini_structured(prompt, model, temperature, max_tokens, response_schema):
    """Send a prompt to Gemini with structured JSON output enforced by a Pydantic schema."""
    client = _ensure_gemini()

    config = {
        "temperature": temperature,
        "response_mime_type": "application/json",
        "response_schema": response_schema,
    }
    if max_tokens is not None:
        config["max_output_tokens"] = max_tokens

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )

    if response.parsed is not None:
        return response.parsed

    parsed = json.loads(response.text)
    return response_schema(**parsed)


def _query_anthropic_structured(prompt, model, temperature, max_tokens, response_schema):
    """Send a prompt to Anthropic with JSON schema instructions appended to the prompt."""
    client = _ensure_anthropic()

    schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
    structured_prompt = (
        f"{prompt}\n\n"
        f"IMPORTANT: Return ONLY valid JSON matching this schema:\n{schema_json}\n"
        f"Return only the JSON object, no additional text."
    )

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": structured_prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens or 4096,
    }

    response = client.messages.create(**kwargs)
    text = response.content[0].text.strip()

    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        text = text[start:end]

    parsed = json.loads(text)
    return response_schema(**parsed)


def query(prompt, profile="smart", temperature=None, max_tokens=None):
    """
    Send a prompt to an LLM and return the response text.

    Uses the profile system defined in config/llm.yaml. Each profile specifies
    a provider (gemini or anthropic) and model name.

    Args:
        prompt: The prompt string to send.
        profile: LLM profile name ("fast", "smart", "creative").
        temperature: Override profile temperature if provided.
        max_tokens: Maximum output tokens if provided.

    Returns:
        Response text string from the LLM.
    """
    llm_config = settings.get_llm_config()
    profile_config = llm_config["profiles"][profile]

    provider = profile_config.get("provider", "gemini")
    model = profile_config["model"]
    temp = temperature if temperature is not None else profile_config.get("temperature", 0.7)

    if provider == "gemini":
        return _query_gemini(prompt, model, temp, max_tokens)
    elif provider == "anthropic":
        return _query_anthropic(prompt, model, temp, max_tokens)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def query_structured(prompt, response_schema, profile="smart", temperature=None, max_tokens=None):
    """
    Send a prompt to an LLM and return a Pydantic model instance.

    Uses Gemini's native JSON schema enforcement or Anthropic's JSON output
    with schema instructions appended to the prompt.

    Args:
        prompt: The prompt string to send.
        response_schema: A Pydantic BaseModel class defining the expected response shape.
        profile: LLM profile name ("fast", "smart", "creative").
        temperature: Override profile temperature if provided.
        max_tokens: Maximum output tokens if provided.

    Returns:
        An instance of response_schema populated with the LLM's response.
    """
    llm_config = settings.get_llm_config()
    profile_config = llm_config["profiles"][profile]

    provider = profile_config.get("provider", "gemini")
    model = profile_config["model"]
    temp = temperature if temperature is not None else profile_config.get("temperature", 0.7)

    if provider == "gemini":
        return _query_gemini_structured(prompt, model, temp, max_tokens, response_schema)
    elif provider == "anthropic":
        return _query_anthropic_structured(prompt, model, temp, max_tokens, response_schema)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
