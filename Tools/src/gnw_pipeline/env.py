from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_if_present(root: Path, filename: str = ".env") -> None:
    """Minimal .env loader (no external deps).

    Only sets keys that are not already present in environment.
    """
    path = root / filename
    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        value = v.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value

