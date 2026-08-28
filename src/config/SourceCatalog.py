"""Load bundled source catalog definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from src.common.utilities import repo_root
    from src.models.catalogs import SourceCatalogEntry, SourceCatalogIndex
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.common.utilities import repo_root
    from src.models.catalogs import SourceCatalogEntry, SourceCatalogIndex

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    yaml = None


@dataclass(frozen=True)
class SourceCatalogContext:
    """Loaded source catalog index and filesystem context."""

    index: SourceCatalogIndex
    catalog_path: str


DEFAULT_SOURCE_CATALOG_PATH = repo_root() / "catalogs" / "sources" / "catalog.yaml"


def _require_yaml_dependency() -> Any:
    if yaml is None:
        raise ModuleNotFoundError(
            "PyYAML is required for source catalog loading. "
            "Install it in your environment (for example: pixi add pyyaml)."
        )
    return yaml


def _load_yaml_mapping(yaml_path: str | Path) -> dict[str, Any]:
    module_yaml = _require_yaml_dependency()
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")

    parsed = module_yaml.safe_load(path.read_text(encoding="utf-8"))
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError(f"YAML at {path} must be a mapping/object.")
    return parsed


def load_catalog_context(
    catalog_path: str | Path = DEFAULT_SOURCE_CATALOG_PATH,
) -> SourceCatalogContext:
    """Load source catalog index and filesystem context."""

    path = Path(catalog_path).resolve()
    parsed = _load_yaml_mapping(path)
    index = SourceCatalogIndex.model_validate(parsed)
    return SourceCatalogContext(index=index, catalog_path=str(path))


def available_sources(
    catalog_path: str | Path = DEFAULT_SOURCE_CATALOG_PATH,
) -> list[str]:
    """Return sorted source IDs in the catalog."""

    context = load_catalog_context(catalog_path)
    return sorted(context.index.sources.keys())


def _entry_definition(
    context: SourceCatalogContext,
    source_id: str,
) -> SourceCatalogEntry:
    entry = context.index.sources.get(source_id)
    if entry is None:
        raise KeyError(
            f"Unknown source ID '{source_id}'. "
            f"Available: {sorted(context.index.sources.keys())}"
        )
    return entry


def load_source(
    source_id: str | None = None,
    *,
    catalog_path: str | Path = DEFAULT_SOURCE_CATALOG_PATH,
) -> SourceCatalogEntry:
    """Load one source entry from the catalog (default entry when id is None)."""

    context = load_catalog_context(catalog_path)
    selected_id = source_id or context.index.default
    return _entry_definition(context, selected_id)
