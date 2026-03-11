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
    """
    Load environment variables from a .env file if it exists.
    
    Parameters:
    	dotenv_path (Path): Path to the .env file to load. If the file exists, its variables are loaded into the process environment without overriding any existing shell environment variables. Defaults to ENV_PATH.
    """
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def get_openai_api_key() -> str:
    """
    Return the OpenAI API key from the environment.
    
    Returns:
        api_key (str): The value of `OPENAI_API_KEY` with surrounding whitespace removed, or an empty string if the variable is not set.
    """
    return os.getenv("OPENAI_API_KEY", "").strip()


def has_openai_api_key() -> bool:
    """
    Determine if an OpenAI API key is configured in the environment.
    
    Returns:
        `true` if an API key is present (non-empty after retrieval), `false` otherwise.
    """
    return bool(get_openai_api_key())


def get_openai_model() -> str:
    """
    Select the OpenAI model name from the environment or fall back to the default.
    
    Returns:
        The model name to use: the value of the `OPENAI_MODEL` environment variable with surrounding
        whitespace removed, or `DEFAULT_MODEL_NAME` if the environment variable is unset or empty.
    """
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME


def get_openai_embedding_model() -> str:
    """
    Selects the embedding model name to use for OpenAI requests.
    
    Reads the `OPENAI_EMBEDDING_MODEL` environment variable, trims surrounding whitespace, and falls back to `DEFAULT_EMBEDDING_MODEL_NAME` if the variable is unset or empty after trimming.
    
    Returns:
        The embedding model name as a string; `DEFAULT_EMBEDDING_MODEL_NAME` when no valid environment value is provided.
    """
    return (
        os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL_NAME).strip()
        or DEFAULT_EMBEDDING_MODEL_NAME
    )


load_environment()
