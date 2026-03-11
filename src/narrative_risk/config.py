"""Configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
SEED_DIR = DATA_DIR / "seed"
CACHE_DIR = DATA_DIR / "cache"
INDEX_PATH = CACHE_DIR / "embedding_index.json"
ENV_PATH = ROOT_DIR / ".env"

DEFAULT_MODEL_NAME = "gpt-4.1-mini"
DEFAULT_EMBEDDING_MODEL_NAME = "text-embedding-3-small"


def load_environment(dotenv_path: Path = ENV_PATH) -> None:
    """Load environment variables from a local .env file without overriding the shell."""
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def get_openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def has_openai_api_key() -> bool:
    return bool(get_openai_api_key())


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME


def get_openai_embedding_model() -> str:
    return (
        os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL_NAME).strip()
        or DEFAULT_EMBEDDING_MODEL_NAME
    )


load_environment()
