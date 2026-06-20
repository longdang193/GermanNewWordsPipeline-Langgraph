from __future__ import annotations

import os
from pathlib import Path
from typing import TypeVar

from pydantic_ai import PromptedOutput
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AuthenticationError

from gnw_pipeline.env import load_dotenv_if_present
from gnw_pipeline.runtime_config import load_runtime_config

OutputT = TypeVar("OutputT")


def normalize_model_name(model_name: str) -> str:
    trimmed = model_name.strip()
    if not trimmed:
        return trimmed
    return trimmed.rsplit("/", 1)[-1]


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


def build_openai_compatible_model(model_name: str, *, root: Path | None = None) -> OpenAIModel:
    repo_root = Path.cwd().resolve() if root is None else root.resolve()
    load_dotenv_if_present(repo_root)
    normalized_model_name = normalize_model_name(model_name)

    provider = OpenAIProvider(
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
        api_key=os.environ.get("OPENAI_API_KEY") or None,
    )
    return OpenAIModel(normalized_model_name, provider=provider)
