from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Nw1RuntimeConfig:
    parallelism: int = 1

@dataclass(frozen=True)
class Nw3RuntimeConfig:
    chunk_size: int = 20
    max_passes: int = 5
    min_see_also_entries: int = 3
    max_see_also_entries: int = 5


@dataclass(frozen=True)
class LlmRuntimeConfig:
    prompted_structured_output_model_prefixes: tuple[str, ...] = ("deepseek-v4-",)


@dataclass(frozen=True)
class RuntimeConfig:
    nw1: Nw1RuntimeConfig = Nw1RuntimeConfig()
    nw3: Nw3RuntimeConfig = Nw3RuntimeConfig()
    llm: LlmRuntimeConfig = LlmRuntimeConfig()


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "Tools" / "scripts" / "run_full_pipeline.py").exists() and (cur / "configs").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def load_runtime_config(*, root: Path | None = None) -> RuntimeConfig:
    repo_root = _find_repo_root(root or Path.cwd())
    path = repo_root / "configs" / "runtime.toml"
    if not path.exists():
        return RuntimeConfig()

    raw = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    nw1_raw = raw.get("nw1") if isinstance(raw, dict) else None
    nw3_raw = raw.get("nw3") if isinstance(raw, dict) else None
    llm_raw = raw.get("llm") if isinstance(raw, dict) else None
    if not isinstance(nw1_raw, dict):
        nw1_raw = {}
    if not isinstance(nw3_raw, dict):
        nw3_raw = {}
    if not isinstance(llm_raw, dict):
        llm_raw = {}

    def _int(source: dict[str, object], key: str, default: int) -> int:
        v = source.get(key, default)
        return int(v) if isinstance(v, (int, float, str)) and str(v).strip() else default

    prefixes_raw = llm_raw.get("prompted_structured_output_model_prefixes", ("deepseek-v4-",))
    prefixes: list[str] = []
    if isinstance(prefixes_raw, (list, tuple)):
        for item in prefixes_raw:
            if isinstance(item, str):
                prefix = item.strip()
                if prefix:
                    prefixes.append(prefix)
    elif isinstance(prefixes_raw, str) and prefixes_raw.strip():
        prefixes.append(prefixes_raw.strip())

    nw1 = Nw1RuntimeConfig(
        parallelism=max(1, _int(nw1_raw, "parallelism", 1)),
    )

    nw3 = Nw3RuntimeConfig(
        chunk_size=max(1, _int(nw3_raw, "chunk_size", 20)),
        max_passes=max(1, _int(nw3_raw, "max_passes", 5)),
        min_see_also_entries=max(1, _int(nw3_raw, "min_see_also_entries", 3)),
        max_see_also_entries=max(1, _int(nw3_raw, "max_see_also_entries", 5)),
    )
    if nw3.max_see_also_entries < nw3.min_see_also_entries:
        nw3 = Nw3RuntimeConfig(
            chunk_size=nw3.chunk_size,
            max_passes=nw3.max_passes,
            min_see_also_entries=nw3.min_see_also_entries,
            max_see_also_entries=nw3.min_see_also_entries,
        )

    llm = LlmRuntimeConfig(
        prompted_structured_output_model_prefixes=tuple(prefixes) or ("deepseek-v4-",),
    )

    return RuntimeConfig(nw1=nw1, nw3=nw3, llm=llm)
