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
        "source_time_ns",
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

    order = np.lexsort((primaries["gun_call_id"], primaries["source_time_ns"]))
    sorted_rows = primaries[order]
    source_time = sorted_rows["source_time_ns"].astype(float)
    interaction_time = sorted_rows["primary_interaction_time_ns"].astype(float)
    interaction_delay = interaction_time - source_time
    finite_delay = _finite(interaction_delay)

    print("\nFirst primary rows sorted by source_time_ns:")
    print(
        "  gun_call_id  track_id  energy_MeV  "
        "source_time_ns  interaction_time_ns  interaction_delay_ns"
    )
    for row, delay in zip(sorted_rows[:rows_to_print], interaction_delay[:rows_to_print]):
        interaction_value = float(row["primary_interaction_time_ns"])
        interaction_text = (
            f"{interaction_value:19.3f}"
            if np.isfinite(interaction_value)
            else "                NaN"
        )
        delay_text = f"{delay:20.3f}" if np.isfinite(delay) else "                 NaN"
        print(
            f"  {int(row['gun_call_id']):11d}"
            f"  {int(row['primary_track_id']):8d}"
            f"  {float(row['primary_energy_MeV']):10.3f}"
            f"  {float(row['source_time_ns']):14.3f}"
            f"  {interaction_text}"
            f"  {delay_text}"
        )

    unique_event_source_times = []
    seen_event_ids: set[int] = set()
    for row in sorted_rows:
        event_id = int(row["gun_call_id"])
        if event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)
        unique_event_source_times.append(float(row["source_time_ns"]))
    event_source_times = np.asarray(unique_event_source_times, dtype=float)

    if event_source_times.size > 1:
        gaps = np.diff(np.sort(event_source_times))
        finite_gaps = _finite(gaps)
        if finite_gaps.size:
            largest_gaps = np.sort(finite_gaps)[-min(5, finite_gaps.size) :]
            print("\nLargest observed gaps between recorded event source times:")
            print("  " + ", ".join(f"{gap:.3f} ns" for gap in largest_gaps))

    if finite_delay.size:
        print("\nInteraction delay summary:")
        print(f"  min:    {np.min(finite_delay):.3f} ns")
        print(f"  median: {np.median(finite_delay):.3f} ns")
        print(f"  max:    {np.max(finite_delay):.3f} ns")
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
