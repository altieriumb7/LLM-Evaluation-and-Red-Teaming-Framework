from src.runtime_settings import live_execution_allowed, load_runtime_settings


def test_demo_mode_disables_live_execution(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ALLOW_LIVE_RUNS", "true")
    settings = load_runtime_settings()
    assert live_execution_allowed(settings, requires_external_api=True) is False


def test_missing_api_key_does_not_crash_settings_load(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = load_runtime_settings()
    assert settings.openai_api_key_present is False


def test_live_execution_requires_allow_flag(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("ALLOW_LIVE_RUNS", "false")
    settings = load_runtime_settings()
    assert live_execution_allowed(settings, requires_external_api=True) is False
    assert live_execution_allowed(settings, requires_external_api=False) is True
