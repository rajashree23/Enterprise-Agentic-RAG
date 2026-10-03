from agentic_rag.config import Settings


def test_settings():
    settings = Settings()

    assert settings.app_name == "agentic-rag"
    assert settings.environment == "local"
