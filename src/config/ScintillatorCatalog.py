"""Load bundled scintillator catalog definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

try:
    from src.common.utilities import repo_root
    from src.models.catalogs import ScintillatorCatalogIndex
    from src.models.scintillator import ScintillatorProperties
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.common.utilities import repo_root
    from src.models.catalogs import ScintillatorCatalogIndex
    from src.models.scintillator import ScintillatorProperties

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - environment dependent
    yaml = None


@dataclass(frozen=True)
class CatalogContext:
    """Loaded catalog index and filesystem context."""

    index: ScintillatorCatalogIndex
    catalog_path: str


DEFAULT_SCINTILLATOR_CATALOG_PATH = (
    repo_root() / "catalogs" / "scintillators" / "catalog.yaml"
)


def _require_yaml_dependency() -> Any:
    if yaml is None:
        raise ModuleNotFoundError(
            "PyYAML is required for scintillator catalog loading. "
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


def _split_curve_line(line: str) -> list[str]:
    """Split one curve row into tokens (supports comma or whitespace)."""

    if "," in line:
        return [token.strip() for token in line.split(",")]
    return [token.strip() for token in line.split()]


def _load_curve(path: Path) -> tuple[list[float], list[float]]:
    if not path.exists():
        raise FileNotFoundError(f"Curve file not found: {path}")

    energy: list[float] = []
    value: list[float] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        tokens = _split_curve_line(line)
        if len(tokens) < 2:
            raise ValueError(
                f"Curve row must have two columns '<energy> <value>', got: {line!r}"
            )

        # Skip a header row like "energy_eV,value".
        if not energy and re.search(r"[A-Za-z_]", tokens[0]):
            continue

        try:
            e = float(tokens[0])
            v = float(tokens[1])
        except ValueError as exc:
            raise ValueError(f"Curve row has non-numeric data: {line!r}") from exc

        energy.append(e)
        value.append(v)

    return energy, value


def _resolve_catalog_path(context: CatalogContext, path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (Path(context.catalog_path).parent / candidate).resolve()


def load_catalog_context(
    catalog_path: str | Path = DEFAULT_SCINTILLATOR_CATALOG_PATH,
) -> CatalogContext:
    """Load scintillator catalog index and filesystem context."""

    path = Path(catalog_path).resolve()
    parsed = _load_yaml_mapping(path)
    index = ScintillatorCatalogIndex.model_validate(parsed)
    return CatalogContext(index=index, catalog_path=str(path))


def available_scintillators(
    catalog_path: str | Path = DEFAULT_SCINTILLATOR_CATALOG_PATH,
) -> list[str]:
    """Return sorted material IDs in the catalog."""

    context = load_catalog_context(catalog_path)
    return sorted(context.index.materials.keys())


def _catalog_material(
    context: CatalogContext,
    material_id: str,
) -> str | ScintillatorProperties:
    material = context.index.materials.get(material_id)
    if material is None:
        raise KeyError(
            f"Unknown scintillator ID '{material_id}'. "
            f"Available: {sorted(context.index.materials.keys())}"
        )
    return material


def load_scintillator_definition(
    material_id: str,
    *,
    catalog_path: str | Path = DEFAULT_SCINTILLATOR_CATALOG_PATH,
) -> ScintillatorProperties:
    """Load one scintillator properties definition from the catalog."""

    context = load_catalog_context(catalog_path)
    material = _catalog_material(context, material_id)
    if isinstance(material, ScintillatorProperties):
        return material

    material_path = _resolve_catalog_path(context, material)
    return ScintillatorProperties.model_validate(_load_yaml_mapping(material_path))


def _hydrate_curve_files(
    material: ScintillatorProperties,
    *,
    context: CatalogContext,
) -> ScintillatorProperties:
    payload = material.model_dump(mode="python", by_alias=True, exclude_none=True)
    reference_energy = material.photon_energy

    curve_files = (
        ("rIndexFile", "rIndex"),
        ("absLengthFile", "absLength"),
        ("scintSpectrumFile", "scintSpectrum"),
    )
    for file_key, value_key in curve_files:
        file_path = payload.pop(file_key, None)
        if file_path is None:
            continue

        energy, values = _load_curve(_resolve_catalog_path(context, file_path))
        if reference_energy is None:
            reference_energy = energy
        elif energy != reference_energy:
            raise ValueError(f"`{file_key}` energy grid does not match `rIndexFile`.")
        payload[value_key] = values

    if reference_energy is not None:
        payload["photonEnergy"] = reference_energy
        payload["nKEntries"] = len(reference_energy)

    return ScintillatorProperties.model_validate(payload)


def load_scintillator(
    material_id: str | None = None,
    *,
    catalog_path: str | Path = DEFAULT_SCINTILLATOR_CATALOG_PATH,
) -> ScintillatorProperties:
    """Load a scintillator entry with file-backed curves hydrated."""

    context = load_catalog_context(catalog_path)
    selected_id = material_id or context.index.default
    material = load_scintillator_definition(selected_id, catalog_path=catalog_path)
    return _hydrate_curve_files(material, context=context)
