from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from openai import AuthenticationError
from pydantic_ai import PromptedOutput
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from gnw_pipeline.env import load_dotenv_if_present
from gnw_pipeline.runtime_config import load_runtime_config

OutputT = TypeVar("OutputT")


@dataclass(frozen=True)
class LlmResolvedSettings:
    api_key: str | None
    base_url: str
    model_name: str


def normalize_model_name(model_name: str) -> str:
    trimmed = model_name.strip()
    if not trimmed:
        return trimmed
    return trimmed.rsplit("/", 1)[-1]


def provider_model_name(model_name: str, *, base_url: str | None) -> str:
    trimmed = model_name.strip()
    if not trimmed:
        return trimmed
    if base_url and "api.openai.com" not in base_url:
        return trimmed
    return normalize_model_name(trimmed)


def model_requires_prompted_output(model_name: str, *, root: Path | None = None) -> bool:
    normalized = normalize_model_name(model_name)
    config = load_runtime_config(root=root)
    return any(
        normalized.startswith(prefix)
        for prefix in config.llm.prompted_structured_output_model_prefixes
    )


def resolve_structured_output(
    model_name: str,
    output_type: type[OutputT],
    *,
    root: Path | None = None,
) -> type[OutputT] | PromptedOutput[OutputT]:
    if model_requires_prompted_output(model_name, root=root):
        return PromptedOutput(output_type)
    return output_type


def classify_openai_compatible_error(exc: BaseException) -> str | None:
    """Classify known OpenAI-compatible failures into stable categories."""
    if isinstance(exc, AuthenticationError):
        return "auth"
    if isinstance(exc, ModelHTTPError) and exc.status_code in {401, 403}:
        return "auth"

    text = str(exc).lower()
    if "authentication fail" in text:
        return "auth"
    if "api key" in text and "invalid" in text:
        return "auth"
    if "status_code: 401" in text or "status code: 401" in text:
        return "auth"
    return None


def _require_env_var(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if value:
        return value
    raise RuntimeError(f"Missing required {name} for LLM runtime.")


def get_llm_runtime_settings(*, root: Path | None = None, require_api_key: bool = False) -> LlmResolvedSettings:
    repo_root = Path.cwd().resolve() if root is None else root.resolve()
    config = load_runtime_config(root=repo_root)
    load_dotenv_if_present(repo_root)

    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip() or None
    base_url = _require_env_var("OPENAI_BASE_URL")
    model_name = _require_env_var("OPENAI_MODEL")

    if require_api_key and config.nw1.enable_llm_enrich and not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY for NW1 LLM enrich.")

    return LlmResolvedSettings(api_key=api_key, base_url=base_url, model_name=model_name)


def build_openai_compatible_model(model_name: str, *, root: Path | None = None) -> OpenAIModel:
    settings = get_llm_runtime_settings(root=root, require_api_key=False)
    effective_model_name = model_name.strip() if model_name.strip() else settings.model_name
    resolved_model_name = provider_model_name(effective_model_name, base_url=settings.base_url)

    provider = OpenAIProvider(
        base_url=settings.base_url,
        api_key=settings.api_key,
    )
    return OpenAIModel(resolved_model_name, provider=provider)
