"""Load and save :class:`src.models.simulation.Simulation` YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

try:
    from src.config.LensCatalog import load_lens
    from src.config.ScintillatorCatalog import load_scintillator
    from src.models.simulation import Simulation
except ModuleNotFoundError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.config.LensCatalog import load_lens
    from src.config.ScintillatorCatalog import load_scintillator
    from src.models.simulation import Simulation


def _hydrate_catalogs(simulation: Simulation) -> Simulation:
    """Hydrate catalog references for scintillator and lenses.

    If a component has a catalog_id but no properties/definition, load from catalog.
    If both catalog_id and inline properties exist, inline takes precedence.
    """
    payload = simulation.model_dump(mode="python", by_alias=False, exclude_none=True)

    # Hydrate scintillator catalog reference
    if simulation.scintillator and simulation.scintillator.catalog_id:
        if simulation.scintillator.properties is None:
            # Load properties from catalog
            scint_properties = load_scintillator(simulation.scintillator.catalog_id)
            payload["scintillator"]["properties"] = scint_properties.model_dump(
                mode="python", by_alias=False, exclude_none=True
            )

    # Hydrate lens catalog references
    if simulation.optical and simulation.optical.lenses:
        hydrated_lenses = []
        for lens in simulation.optical.lenses:
            if lens.catalog_id:
                # Load full lens definition from catalog with resolved file paths
                catalog_lens = load_lens(lens.catalog_id)
                # Merge: catalog provides base, inline overrides
                lens_dict = catalog_lens.model_dump(
                    mode="python", by_alias=False, exclude_none=True
                )
                # Override with any inline properties
                inline_dict = lens.model_dump(
                    mode="python", by_alias=False, exclude_none=True
                )
                lens_dict.update(inline_dict)
                hydrated_lenses.append(lens_dict)
            else:
                # No catalog reference, keep as-is
                hydrated_lenses.append(
                    lens.model_dump(mode="python", by_alias=False, exclude_none=True)
                )
        payload["optical"]["lenses"] = hydrated_lenses

    return Simulation.model_validate(payload)


def from_yaml(yaml_path: str | Path, *, hydrate_catalogs: bool = True) -> Simulation:
    """Load a YAML file and validate it as ``Simulation``.

    Args:
        yaml_path: Path to YAML configuration file
        hydrate_catalogs: If True, automatically load catalog references for
            scintillator and lens definitions. Default is True.

    Returns:
        Validated Simulation model with catalog references hydrated
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML config file not found: {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(
            f"YAML config at {path} must be a mapping/object at top level."
        )

    simulation = Simulation.model_validate(payload)

    if hydrate_catalogs:
        simulation = _hydrate_catalogs(simulation)

    return simulation


def write_yaml(
    config: Simulation,
    yaml_path: str | Path,
    *,
    overwrite: bool = True,
) -> None:
    """Write a ``Simulation`` to a YAML file."""

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
