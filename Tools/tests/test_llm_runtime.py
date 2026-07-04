from __future__ import annotations

from pathlib import Path

from pydantic_ai import PromptedOutput

import gnw_pipeline.llm_runtime as llm_runtime
from gnw_pipeline.llm_runtime import (
    classify_openai_compatible_error,
    get_llm_runtime_settings,
    normalize_model_name,
    resolve_structured_output,
)
from gnw_pipeline.nw1_llm_enrich import EnrichedOverride
from gnw_pipeline.nw1_llm_qa import ReviewResult


def test_normalize_model_name_uses_last_segment() -> None:
    assert normalize_model_name("ds/deepseek-v4-flash") == "deepseek-v4-flash"


def test_resolve_structured_output_uses_prompted_output_for_deepseek_v4() -> None:
    output = resolve_structured_output("ds/deepseek-v4-flash", EnrichedOverride)

    assert isinstance(output, PromptedOutput)


def test_resolve_structured_output_preserves_default_mode_for_openai_models() -> None:
    output = resolve_structured_output("gpt-4o-mini", ReviewResult)

    assert output is ReviewResult


def test_classify_openai_compatible_error_detects_model_http_auth() -> None:
    from pydantic_ai.exceptions import ModelHTTPError

    exc = ModelHTTPError(
        status_code=401,
        model_name="ds/deepseek-v4-flash",
        body={"message": "Authentication failed"},
    )

    assert classify_openai_compatible_error(exc) == "auth"


def test_build_openai_compatible_model_normalizes_model_name(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, *, base_url=None, api_key=None):
            captured["base_url"] = base_url
            captured["api_key"] = api_key

    class FakeModel:
        def __init__(self, model_name, *, provider):
            captured["model_name"] = model_name
            captured["provider"] = provider

    monkeypatch.setattr(llm_runtime, "OpenAIProvider", FakeProvider)
    monkeypatch.setattr(llm_runtime, "OpenAIModel", FakeModel)
    monkeypatch.setattr(
        llm_runtime,
        "get_llm_runtime_settings",
        lambda **_kwargs: llm_runtime.LlmResolvedSettings(
            api_key="k",
            base_url="https://api.openai.com/v1",
            model_name="ds/deepseek-v4-flash",
        ),
    )

    model = llm_runtime.build_openai_compatible_model("ds/deepseek-v4-flash")

    assert captured["model_name"] == "deepseek-v4-flash"
    assert isinstance(model, FakeModel)


def test_build_openai_compatible_model_preserves_prefixed_model_for_custom_base_url(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, *, base_url=None, api_key=None):
            captured["base_url"] = base_url
            captured["api_key"] = api_key

    class FakeModel:
        def __init__(self, model_name, *, provider):
            captured["model_name"] = model_name
            captured["provider"] = provider

    monkeypatch.setattr(llm_runtime, "OpenAIProvider", FakeProvider)
    monkeypatch.setattr(llm_runtime, "OpenAIModel", FakeModel)
    monkeypatch.setattr(
        llm_runtime,
        "get_llm_runtime_settings",
        lambda **_kwargs: llm_runtime.LlmResolvedSettings(
            api_key="k",
            base_url="http://127.0.0.1:20128/v1",
            model_name="cx/gpt-5.4-mini",
        ),
    )

    model = llm_runtime.build_openai_compatible_model("", root=Path("."))

    assert captured["model_name"] == "cx/gpt-5.4-mini"
    assert isinstance(model, FakeModel)


def test_get_llm_runtime_settings_requires_base_url(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "configs").mkdir(parents=True)
    monkeypatch.setenv("OPENAI_MODEL", "cx/gpt-5.4-mini")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        get_llm_runtime_settings(root=tmp_path)
    except RuntimeError as exc:
        assert "OPENAI_BASE_URL" in str(exc)
    else:
        raise AssertionError("Expected missing OPENAI_BASE_URL to fail.")


def test_get_llm_runtime_settings_requires_model(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "configs").mkdir(parents=True)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:20128/v1")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        get_llm_runtime_settings(root=tmp_path)
    except RuntimeError as exc:
        assert "OPENAI_MODEL" in str(exc)
    else:
        raise AssertionError("Expected missing OPENAI_MODEL to fail.")


def test_get_llm_runtime_settings_uses_explicit_env_values(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "configs").mkdir(parents=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:20128/v1")
    monkeypatch.setenv("OPENAI_MODEL", "cx/gpt-5.4-mini")

    settings = get_llm_runtime_settings(root=tmp_path)

    assert settings.api_key == "test-key"
    assert settings.base_url == "http://127.0.0.1:20128/v1"
    assert settings.model_name == "cx/gpt-5.4-mini"


def test_get_llm_runtime_settings_requires_api_key_when_enabled(monkeypatch, tmp_path: Path) -> None:
    cfg_path = tmp_path / "configs"
    cfg_path.mkdir(parents=True)
    (cfg_path / "runtime.toml").write_text(
        '[nw1]\nenable_llm_enrich = true\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:20128/v1")
    monkeypatch.setenv("OPENAI_MODEL", "cx/gpt-5.4-mini")

    try:
        get_llm_runtime_settings(root=tmp_path, require_api_key=True)
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing API key to fail when NW1 enrich is enabled.")
