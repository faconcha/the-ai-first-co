from crewai import LLM

from shared import settings


_config = None


def _get_config() -> dict:
    global _config
    if _config is None:
        _config = settings.get_llm_config()
    return _config


def get_llm(profile: str) -> LLM:
    config = _get_config()
    if profile not in config["profiles"]:
        raise ValueError(f"LLM profile '{profile}' not found. Available: {list(config['profiles'].keys())}")

    profile_config = config["profiles"][profile]
    return LLM(
        model=profile_config["model"],
        temperature=profile_config.get("temperature", 0.7),
    )
