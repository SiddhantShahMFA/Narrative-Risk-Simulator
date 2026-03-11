from __future__ import annotations

from pathlib import Path

from narrative_risk import config


def test_load_environment_reads_dotenv_file(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=from-dotenv\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config.load_environment(env_path)

    assert config.get_openai_api_key() == "from-dotenv"
    assert config.has_openai_api_key() is True


def test_existing_process_environment_wins_over_dotenv(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "from-shell")

    config.load_environment(env_path)

    assert config.get_openai_api_key() == "from-shell"


def test_optional_model_defaults_apply_when_env_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)

    assert config.get_openai_model() == config.DEFAULT_MODEL_NAME
    assert config.get_openai_embedding_model() == config.DEFAULT_EMBEDDING_MODEL_NAME
