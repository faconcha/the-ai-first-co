import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_DIR = PROJECT_ROOT / "output"

load_dotenv(PROJECT_ROOT / ".env")


def load_yaml(filename: str) -> dict:
    filepath = CONFIG_DIR / filename
    with open(filepath, "r") as f:
        return yaml.safe_load(f)


def get_company_config(company: str = "bison") -> dict:
    return load_yaml(f"{company}.yaml")


def get_llm_config() -> dict:
    return load_yaml("llm.yaml")


def ensure_output_dir(product: str) -> Path:
    path = OUTPUT_DIR / product
    path.mkdir(parents=True, exist_ok=True)
    return path
