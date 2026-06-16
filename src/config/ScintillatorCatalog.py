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
    """Transform catalog nested format to simulation nested format.

    Catalog format:
        composition.density: ValueWithUnit
        optical.curves: OpticalCurves (CurveReference objects)
        optical.constants: OpticalConstants (scintYield as ValueWithUnit)

    Simulation format:
        composition.density: float
        optical.photon_energy, optical.r_index, etc.: list[float]
        optical.scint_yield: float
    """
    from src.common.utilities import (
        convert_density_to_g_cm3,
        convert_scint_yield_to_per_mev,
        ValueWithUnit,
    )

    payload = material.model_dump(mode="python", by_alias=False, exclude_none=True)

    # Transform composition.density from ValueWithUnit to float
    if "composition" in payload and "density" in payload["composition"]:
        density_obj = material.composition.density
        if isinstance(density_obj, ValueWithUnit):
            payload["composition"]["density"] = convert_density_to_g_cm3(
                density_obj.value, density_obj.unit
            )

    # Transform optical properties from catalog format to simulation format
    if "optical" in payload:
        optical = payload["optical"]
        reference_energy = None

        # Load curves from file references
        if "curves" in optical:
            curves = optical["curves"]

            # Load rIndex curve (required)
            if "r_index" in curves:
                r_index_ref = curves["r_index"]
                energy, r_index_values = _load_curve(
                    _resolve_catalog_path(context, r_index_ref["path"])
                )
                reference_energy = energy
                optical["r_index"] = r_index_values

            # Load absLength curve (optional)
            if "abs_length" in curves:
                abs_length_ref = curves["abs_length"]
                energy, abs_length_values = _load_curve(
                    _resolve_catalog_path(context, abs_length_ref["path"])
                )
                if reference_energy is not None and energy != reference_energy:
                    raise ValueError("absLength energy grid does not match rIndex.")
                optical["abs_length"] = abs_length_values

            # Load scintSpectrum curve (optional)
            if "scint_spectrum" in curves:
                scint_spectrum_ref = curves["scint_spectrum"]
                energy, scint_spectrum_values = _load_curve(
                    _resolve_catalog_path(context, scint_spectrum_ref["path"])
                )
                if reference_energy is not None and energy != reference_energy:
                    raise ValueError("scintSpectrum energy grid does not match rIndex.")
                optical["scint_spectrum"] = scint_spectrum_values

            # Remove curves wrapper after extraction
            del optical["curves"]

        # Extract constants from nested structure
        if "constants" in optical:
            constants = optical["constants"]

            # Extract scint_yield from ValueWithUnit
            if "scint_yield" in constants:
                scint_yield_obj = material.optical.constants.scint_yield
                if isinstance(scint_yield_obj, ValueWithUnit):
                    optical["scint_yield"] = convert_scint_yield_to_per_mev(
                        scint_yield_obj.value, scint_yield_obj.unit
                    )
                else:
                    optical["scint_yield"] = scint_yield_obj

            # Copy resolution_scale directly
            if "resolution_scale" in constants:
                optical["resolution_scale"] = constants["resolution_scale"]

            # Copy time_components directly (already compatible)
            if "time_components" in constants:
                optical["time_components"] = constants["time_components"]

            # Remove constants wrapper after extraction
            del optical["constants"]

        # Set photon_energy and n_k_entries if we loaded curves
        if reference_energy is not None:
            optical["photon_energy"] = reference_energy
            optical["n_k_entries"] = len(reference_energy)

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
