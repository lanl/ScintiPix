"""Run and inspect a lightweight Geant4 source/neutron timing example."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

try:
    import h5py
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    raise ModuleNotFoundError(
        "h5py is required for this example. Run with `pixi run python ...`."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from src.config.ConfigIO import from_yaml  # noqa: E402
from src.config.ConfigIO import resolve_run_environment_paths  # noqa: E402
from src.config.ConfigIO import simulated_output_filename  # noqa: E402
from src.config.SimConfig import SimulationConfig  # noqa: E402
from src.runner.runSimulation import run_simulation  # noqa: E402


CONFIG_PATH = REPO_ROOT / "examples" / "yamlFiles" / "pulsed_neutron_source_timing.yaml"
RUN_GEANT4 = True
BEAM_ON_OVERRIDE: int | None = None
ROWS_TO_PRINT = 12


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run and inspect Geant4 source/neutron timing from one YAML file."
    )
    parser.add_argument(
        "yaml_path",
        nargs="?",
        type=Path,
        default=CONFIG_PATH,
        help="SimConfig YAML path.",
    )
    return parser.parse_args()


def _apply_beam_override(config, beam_on: int | None) -> None:
    if beam_on is None:
        return
    if beam_on <= 0:
        raise ValueError("BEAM_ON_OVERRIDE must be greater than zero.")
    if config.simulation is None:
        config.simulation = SimulationConfig(number_of_particles=beam_on)
    else:
        config.simulation.number_of_particles = beam_on


def _output_hdf5_path(config) -> Path:
    run_paths = resolve_run_environment_paths(config)
    return (run_paths.simulated_photons / simulated_output_filename(config)).resolve()


def _require_fields(dtype_names: tuple[str, ...] | None) -> None:
    if dtype_names is None:
        raise ValueError("/primaries is not a compound dataset.")
    missing = {
        "gun_call_id",
        "primary_track_id",
        "primary_energy_MeV",
        "primary_interaction_time_ns",
    } - set(dtype_names)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"/primaries is missing required fields: {missing_list}")


def _finite(values: np.ndarray) -> np.ndarray:
    return values[np.isfinite(values)]


def _print_timing_summary(hdf5_path: Path, rows_to_print: int) -> None:
    if not hdf5_path.exists():
        raise FileNotFoundError(f"Expected HDF5 output does not exist: {hdf5_path}")

    with h5py.File(hdf5_path, "r") as handle:
        if "primaries" not in handle:
            raise ValueError(f"{hdf5_path} does not contain /primaries.")
        primaries = handle["primaries"][:]

    _require_fields(primaries.dtype.names)

    print(f"HDF5: {hdf5_path}")
    print(f"/primaries rows: {len(primaries)}")
    if len(primaries) == 0:
        print(
            "No neutron primaries produced recorded scintillator secondary activity. "
            "Increase BEAM_ON_OVERRIDE for a denser timing sample."
        )
        return

    interaction_time = primaries["primary_interaction_time_ns"].astype(float)
    order = np.lexsort((primaries["gun_call_id"], interaction_time))
    sorted_rows = primaries[order]
    sorted_interaction_time = sorted_rows["primary_interaction_time_ns"].astype(float)
    finite_interaction_time = _finite(sorted_interaction_time)

    print("\nFirst primary rows sorted by primary_interaction_time_ns:")
    print(
        "  gun_call_id  track_id  energy_MeV  "
        "primary_interaction_time_ns"
    )
    for row in sorted_rows[:rows_to_print]:
        interaction_value = float(row["primary_interaction_time_ns"])
        interaction_text = (
            f"{interaction_value:27.3f}"
            if np.isfinite(interaction_value)
            else "                        NaN"
        )
        print(
            f"  {int(row['gun_call_id']):11d}"
            f"  {int(row['primary_track_id']):8d}"
            f"  {float(row['primary_energy_MeV']):10.3f}"
            f"  {interaction_text}"
        )

    if finite_interaction_time.size > 1:
        gaps = np.diff(np.sort(finite_interaction_time))
        finite_gaps = _finite(gaps)
        if finite_gaps.size:
            largest_gaps = np.sort(finite_gaps)[-min(5, finite_gaps.size) :]
            print("\nLargest observed gaps between recorded interaction times:")
            print("  " + ", ".join(f"{gap:.3f} ns" for gap in largest_gaps))

    if finite_interaction_time.size:
        print("\nPrimary interaction time summary:")
        print(f"  min:    {np.min(finite_interaction_time):.3f} ns")
        print(f"  median: {np.median(finite_interaction_time):.3f} ns")
        print(f"  max:    {np.max(finite_interaction_time):.3f} ns")
    else:
        print("\nNo finite primary_interaction_time_ns values were recorded.")


def main() -> None:
    args = _parse_args()
    if ROWS_TO_PRINT <= 0:
        raise ValueError("ROWS_TO_PRINT must be greater than zero.")

    config = from_yaml(args.yaml_path.expanduser().resolve())
    _apply_beam_override(config, BEAM_ON_OVERRIDE)
    hdf5_path = _output_hdf5_path(config)

    if RUN_GEANT4:
        run_simulation(config)

    _print_timing_summary(hdf5_path, ROWS_TO_PRINT)


if __name__ == "__main__":
    main()
