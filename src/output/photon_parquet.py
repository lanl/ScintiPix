"""Write a HERMES-style photon parquet file with ground-truth labels.

HERMES writes one parquet row per detected optical photon. This module produces
the same photon table from a finished ScintiPix run and adds truth columns that
record which incident particle caused each photon, so photon-clustering
algorithms can be tested against known ground truth.

This is also where events are placed on a shared clock. Geant4 times every event
from zero: the moment its source fired is time zero for that event, and the
interaction time, photon creation times, and photon arrival times are all
measured from there. This step reads `source.timing` from the configuration the
run saved, decides when in the run each event happened, and adds that time to
every photon arrival:

    time in the run = time assigned to the event + time recorded by Geant4

The photon table columns match HERMES exactly:

    photon_id, x, y, timestamp_canonical, tot, quality_flags

and the truth columns added here are:

    cluster_id, primary_track_id, secondary_track_id, event_time_ns, event_type

`tot` and `quality_flags` are placeholders (0): the intensifier and sensor
stages that would fill them are not implemented yet. The columns are present so
downstream HERMES code reads the same schema.
"""

import math
from pathlib import Path
import zlib

import numpy as np
import pandas as pd
from loguru import logger

from src.config.yaml import from_yaml
from src.models.simulation import Simulation
from src.optics.io import (
    HEADER_SIZE,
    read_transported_photons,
    validate_binary_header,
)

# One HERMES canonical time tick is 25 ns / 12288 (about 2.0345 ps). A photon
# time in nanoseconds is divided by this to get the canonical tick count.
CANONICAL_TICK_NS = 25.0 / 12288.0

NS_PER_SECOND = 1_000_000_000.0
MM_PER_CM = 10.0

# Conventional locations inside a run directory (see WorkingDirectoryLayout).
TRANSPORTED_PHOTONS_PATH = Path("transportedPhotons") / "photons.bin"
PRIMARIES_PATH = Path("primaries") / "primaries.bin"
CONFIG_DIRECTORY = Path("config")

OUTPUT_FILENAME = "photons.parquet"

# Layout of one record in primaries.bin (matches the C++ primary struct and
# scripts/read_binary_output.py). Only gun_call_id, primary_track_id, and
# primary_species are used here, but the whole record is described so the fixed
# record size matches the file.
PRIMARY_DTYPE = np.dtype(
    [
        ("gun_call_id", "<i8"),
        ("primary_track_id", "<i4"),
        ("_padding0", "V4"),
        ("primary_species", "S24"),
        ("primary_x_mm", "<f8"),
        ("primary_y_mm", "<f8"),
        ("primary_energy_MeV", "<f8"),
        ("primary_interaction_time_ns", "<f8"),
        ("primary_created_secondary_count", "<i8"),
        ("primary_generated_optical_photon_count", "<i8"),
        ("primary_detected_optical_interface_photon_count", "<i8"),
    ]
)


def _read_primary_species(primaries_path: Path) -> pd.DataFrame:
    """Read primaries.bin and return one row of (cluster_id, primary_track_id, event_type)."""

    record_count = validate_binary_header(primaries_path, PRIMARY_DTYPE)
    records = np.fromfile(
        primaries_path,
        dtype=PRIMARY_DTYPE,
        count=record_count,
        offset=HEADER_SIZE,
    )
    species = [
        raw.decode("utf-8").rstrip("\x00") for raw in records["primary_species"]
    ]
    return pd.DataFrame(
        {
            "cluster_id": records["gun_call_id"],
            "primary_track_id": records["primary_track_id"],
            "event_type": species,
        }
    )


def _read_run_config(run_directory: Path) -> Simulation:
    """Load the configuration that produced this run from its config directory."""

    config_directory = run_directory / CONFIG_DIRECTORY
    saved_configs = sorted(config_directory.glob("*.yaml"))
    if len(saved_configs) != 1:
        found = ", ".join(path.name for path in saved_configs) or "nothing"
        raise FileNotFoundError(
            f"Expected exactly one saved configuration in {config_directory}, "
            f"found {found}. Event times cannot be assigned without knowing which "
            "settings the run used."
        )
    return from_yaml(saved_configs[0])


def _source_area_cm2(config: Simulation) -> float:
    """Return the area of the source disc the particles are fired from."""

    radius_cm = config.source.gps.position.radius_mm / MM_PER_CM
    return math.pi * radius_cm * radius_cm


def _source_particle_rate_per_second(config: Simulation) -> float:
    """Return how many particles the source fires per second.

    `particle_flux` is per square centimetre per second, so the rate depends on
    how large the source disc is.
    """

    timing = config.source.timing
    if timing is None or timing.particle_flux is None:
        raise ValueError(
            "`source.timing.particle_flux` is required to derive source timing."
        )
    return timing.particle_flux * _source_area_cm2(config)


def _mean_event_spacing_ns(config: Simulation) -> float:
    """Return the average gap between two fired particles, in nanoseconds."""

    particle_rate_per_second = _source_particle_rate_per_second(config)
    if particle_rate_per_second <= 0.0:
        raise ValueError("Derived source particle rate must be greater than zero.")
    return NS_PER_SECOND / particle_rate_per_second


def _particles_per_pulse(config: Simulation) -> int:
    """Return how many particles one pulse window holds."""

    timing = config.source.timing
    if timing is None or timing.pulse_period_ns is None:
        raise ValueError(
            "`source.timing.pulse_period_ns` is required for pulsed source timing."
        )
    expected_particles = (
        _source_particle_rate_per_second(config)
        * timing.pulse_period_ns
        / NS_PER_SECOND
    )
    return max(1, int(math.ceil(expected_particles - 1.0e-12)))


def _fired_event_count(config: Simulation) -> int:
    """Return how many particles the run fired.

    Every fired particle is one event and takes up its own place on the clock,
    including the great majority that put no light on the photocathode, so the
    count has to come from the configuration rather than from the photons.
    """

    event_count = config.geant4runner.number_of_particles
    if event_count is None:
        raise ValueError(
            "`geant4runner.number_of_particles` is required to assign event times."
        )
    return int(event_count)


def _run_random_numbers(config: Simulation) -> np.random.Generator:
    """Return random numbers seeded from the run's own name.

    Running this step again on the same run directory reproduces the same event
    times; a different run or sub-run gets a different set.
    """

    run_environment = config.metadata.run_environment
    run_name = (
        f"{run_environment.simulation_run_id}_"
        f"{run_environment.sub_run_number:03d}"
    )
    return np.random.default_rng(zlib.crc32(run_name.encode("utf-8")))


def _event_times_ns(config: Simulation) -> np.ndarray:
    """Return the time in the run at which each event's source fired.

    `none` leaves every event at zero, which is exactly what Geant4 recorded, so
    the output is unchanged. `continuous` separates events by random gaps drawn
    from an exponential distribution, the way a steady source arrives. `pulsed`
    fills one pulse window at a time, spreading the events evenly across the
    width of the window.
    """

    timing = config.source.timing
    event_count = _fired_event_count(config)
    if timing is None or timing.mode == "none":
        return np.zeros(event_count, dtype=np.float64)

    random_numbers = _run_random_numbers(config)

    if timing.mode == "continuous":
        gaps_ns = random_numbers.exponential(
            _mean_event_spacing_ns(config), size=event_count
        )
        return timing.start_time_ns + np.cumsum(gaps_ns)

    # Pulsed. `pulse_shape` only allows "uniform", so events are spread evenly
    # across the window.
    pulse_index = np.arange(event_count) // _particles_per_pulse(config)
    window_start_ns = (
        timing.start_time_ns
        + pulse_index * timing.pulse_period_ns
        + timing.pulse_time_offset_ns
    )
    time_in_window_ns = random_numbers.uniform(
        0.0, timing.pulse_time_width_ns, size=event_count
    )
    return window_start_ns + time_in_window_ns


def write_photon_parquet(run_directory: str | Path) -> Path:
    """Write ``photons.parquet`` for a finished run and return its path.

    Reads the transported photons, the primaries, and the saved configuration
    from their conventional locations in ``run_directory``, assigns each event
    its time in the run, labels each photon with the incident particle that
    caused it, and writes the HERMES-style photon table plus truth columns to
    ``run_directory/photons.parquet``.
    """

    run_directory = Path(run_directory)
    transported_path = run_directory / TRANSPORTED_PHOTONS_PATH
    primaries_path = run_directory / PRIMARIES_PATH

    photons = read_transported_photons(transported_path)
    primary_species = _read_primary_species(primaries_path)

    config = _read_run_config(run_directory)
    event_times_ns = _event_times_ns(config)

    cluster_id = photons["gun_call_id"]
    if len(cluster_id) and int(cluster_id.max()) >= len(event_times_ns):
        raise ValueError(
            f"{transported_path.name} holds event {int(cluster_id.max())}, but the "
            f"saved configuration fired only {len(event_times_ns)} events. The "
            "configuration does not describe this run."
        )
    photon_event_time_ns = event_times_ns[cluster_id]

    photon_table = pd.DataFrame(
        {
            "photon_id": np.arange(len(photons), dtype=np.uint64),
            "x": photons["photocathode_hit_x_mm"].astype(np.float64),
            "y": photons["photocathode_hit_y_mm"].astype(np.float64),
            "timestamp_canonical": (
                photon_event_time_ns + photons["photocathode_hit_time_ns"]
            )
            / CANONICAL_TICK_NS,
            "tot": np.zeros(len(photons), dtype=np.uint64),
            "quality_flags": np.zeros(len(photons), dtype=np.uint16),
            "cluster_id": cluster_id,
            "primary_track_id": photons["primary_track_id"],
            "secondary_track_id": photons["secondary_track_id"],
            "event_time_ns": photon_event_time_ns,
        }
    )

    labeled = photon_table.merge(
        primary_species,
        on=["cluster_id", "primary_track_id"],
        how="left",
    )

    unlabeled_count = int(labeled["event_type"].isna().sum())
    if unlabeled_count:
        logger.warning(
            "{} of {} photons had no matching primary in {}; their event_type is empty.",
            unlabeled_count,
            len(labeled),
            primaries_path.name,
        )
    labeled["event_type"] = labeled["event_type"].fillna("")

    timing_mode = "none" if config.source.timing is None else config.source.timing.mode
    output_path = run_directory / OUTPUT_FILENAME
    labeled.to_parquet(output_path, index=False)
    logger.info(
        "Wrote {} photons to {} with '{}' source timing",
        len(labeled),
        output_path,
        timing_mode,
    )
    return output_path
