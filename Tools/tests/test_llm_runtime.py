from __future__ import annotations

from pydantic_ai import PromptedOutput

import gnw_pipeline.llm_runtime as llm_runtime
from gnw_pipeline.llm_runtime import (
    classify_openai_compatible_error,
    normalize_model_name,
    resolve_structured_output,
)
from gnw_pipeline.nw1_llm_enrich import EnrichedOverride
from gnw_pipeline.nw1_llm_qa import ReviewResult


def test_normalize_model_name_uses_last_segment():
    assert normalize_model_name("ds/deepseek-v4-flash") == "deepseek-v4-flash"


def test_resolve_structured_output_uses_prompted_output_for_deepseek_v4():
    output = resolve_structured_output("ds/deepseek-v4-flash", EnrichedOverride)

    assert isinstance(output, PromptedOutput)


def test_resolve_structured_output_preserves_default_mode_for_openai_models():
    output = resolve_structured_output("gpt-4o-mini", ReviewResult)

    assert output is ReviewResult


def test_classify_openai_compatible_error_detects_model_http_auth():
    from pydantic_ai.exceptions import ModelHTTPError

    exc = ModelHTTPError(
        status_code=401,
        model_name="ds/deepseek-v4-flash",
        body={"message": "Authentication failed"},
    )

    assert classify_openai_compatible_error(exc) == "auth"


def test_build_openai_compatible_model_normalizes_model_name(monkeypatch):
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

    model = llm_runtime.build_openai_compatible_model("ds/deepseek-v4-flash")

    assert captured["model_name"] == "deepseek-v4-flash"
    assert isinstance(model, FakeModel)
