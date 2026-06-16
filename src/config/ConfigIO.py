"""Load and save :class:`src.config.SimConfig.SimConfig` YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml
from models.Simulation import SimConfig


def from_yaml(yaml_path: str | Path) -> SimConfig:
    """Load a YAML file and validate it as ``SimConfig``."""

    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML config file not found: {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(
            f"YAML config at {path} must be a mapping/object at top level."
        )

    return SimConfig.model_validate(payload)


def write_yaml(
    config: SimConfig,
    yaml_path: str | Path,
    *,
    overwrite: bool = True,
) -> None:
    """Write a ``SimConfig`` to a YAML file."""

    path = Path(yaml_path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            config.model_dump(mode="python", by_alias=True),
            sort_keys=False,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )


__all__ = ["from_yaml", "write_yaml"]
