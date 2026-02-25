from __future__ import annotations
from pathlib import Path


def load_highscore(path: str) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    try:
        s = p.read_text(encoding="utf-8").strip()
        return int(s) if s else 0
    except (OSError, ValueError):
        return 0


def save_highscore(path: str, value: int) -> None:
    try:
        Path(path).write_text(str(int(value)), encoding="utf-8")
    except OSError:
        pass