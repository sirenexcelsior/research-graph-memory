from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def find_project_root(start: Path | None = None) -> Path:
    env_home = os.getenv("RGM_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()

    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "rgm").exists():
            return candidate
    return current


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RGMConfig:
    root: Path
    db_path: Path
    graph_path: Path
    raw_dir: Path
    processed_dir: Path
    configs_dir: Path

    @classmethod
    def load(cls, root: Path | None = None) -> "RGMConfig":
        project_root = find_project_root(root)
        db_path = Path(os.getenv("RGM_DB_PATH", project_root / "data" / "indexes" / "rgm.sqlite"))
        graph_path = Path(os.getenv("RGM_GRAPH_PATH", project_root / "data" / "indexes" / "graph.pkl"))
        return cls(
            root=project_root,
            db_path=db_path.expanduser().resolve(),
            graph_path=graph_path.expanduser().resolve(),
            raw_dir=project_root / "data" / "raw",
            processed_dir=project_root / "data" / "processed",
            configs_dir=project_root / "configs",
        )

    def ensure_dirs(self) -> None:
        for path in [
            self.db_path.parent,
            self.graph_path.parent,
            self.raw_dir / "holographic",
            self.raw_dir / "notes",
            self.raw_dir / "experiments",
            self.raw_dir / "chats",
            self.processed_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def read_yaml(self, name: str) -> dict[str, Any]:
        path = self.configs_dir / name
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
