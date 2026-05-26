from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Nw3RuntimeConfig:
    chunk_size: int = 20
    max_passes: int = 5
    min_see_also_entries: int = 3
    max_see_also_entries: int = 5


@dataclass(frozen=True)
class RuntimeConfig:
    nw3: Nw3RuntimeConfig = Nw3RuntimeConfig()


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
    nw3_raw = raw.get("nw3") if isinstance(raw, dict) else None
    if not isinstance(nw3_raw, dict):
        return RuntimeConfig()

    def _int(key: str, default: int) -> int:
        v = nw3_raw.get(key, default)
        return int(v) if isinstance(v, (int, float, str)) and str(v).strip() else default

    nw3 = Nw3RuntimeConfig(
        chunk_size=max(1, _int("chunk_size", 20)),
        max_passes=max(1, _int("max_passes", 5)),
        min_see_also_entries=max(1, _int("min_see_also_entries", 3)),
        max_see_also_entries=max(1, _int("max_see_also_entries", 5)),
    )
    if nw3.max_see_also_entries < nw3.min_see_also_entries:
        nw3 = Nw3RuntimeConfig(
            chunk_size=nw3.chunk_size,
            max_passes=nw3.max_passes,
            min_see_also_entries=nw3.min_see_also_entries,
            max_see_also_entries=nw3.min_see_also_entries,
        )

    return RuntimeConfig(nw3=nw3)

