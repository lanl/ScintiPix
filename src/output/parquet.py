"""Write each stage's table as parquet, with every time on one shared run clock.

Geant4 times every event from zero: the moment its source fired is time zero for
that event, and the interaction time, photon creation times, and photon arrival
times are all measured from there. The binary files keep those times exactly as
they were recorded. This module reads `source.timing` from the configuration,
decides when in the run each event happened, and writes a parquet copy of every
stage whose times are on the run clock:

    time in the run = time assigned to the event + time recorded by Geant4

Each parquet table carries an `event_time_ns` column holding the time assigned to
that row's event, so the original event-relative time is still recoverable by
subtraction.

Three tables are written, one per stage that records a time:

    primaries/primaries.parquet             primary_interaction_time_ns
    simulatedPhotons/photons.parquet        photon_creation_time_ns,
                                            optical_interface_hit_time_ns
    photons.parquet                         timestamp_canonical

Secondary particles record no time, so no table is written for them.

`photons.parquet` sits at the top of the run directory because it is the table
HERMES reads. HERMES writes one row per detected optical photon with the columns

    photon_id, x, y, timestamp_canonical, tot, quality_flags

and the truth columns added here record which incident particle caused each
photon, so photon-clustering algorithms can be tested against known ground truth:

    cluster_id, primary_track_id, secondary_track_id, event_time_ns, event_type

`cluster_id` is the same event id the other tables call `gun_call_id`. `tot` and
`quality_flags` are placeholders (0): the intensifier and sensor stages that would
fill them are not implemented yet. The columns are present so downstream HERMES
code reads the same columns it always does.
"""

import math
from pathlib import Path
import zlib

import numpy as np
import pandas as pd
from loguru import logger

from src.models.simulation import Simulation
from src.optics.io import (
    HEADER_SIZE,
    read_simulated_photons,
    read_transported_photons,
    validate_binary_header,
)

# One HERMES canonical time tick is 25 ns / 12288 (about 2.0345 ps). A photon
# time in nanoseconds is divided by this to get the canonical tick count.
CANONICAL_TICK_NS = 25.0 / 12288.0

NS_PER_SECOND = 1_000_000_000.0
MM_PER_CM = 10.0

# The photon table HERMES reads sits at the top of the run directory.
PHOTON_TABLE_FILENAME = "photons.parquet"

# Layout of one record in primaries.bin (matches the C++ primary struct and
# scripts/read_binary_output.py).
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


def _table_from_records(records: np.ndarray) -> pd.DataFrame:
    """Turn one binary table into a DataFrame with the same column names.

    Padding fields present only to keep the record size fixed are dropped, and
    text fields are decoded from their fixed-width bytes.
    """

    columns: dict[str, object] = {}
    for name in records.dtype.names:
        if name.startswith("_"):
            continue
        values = records[name]
        if values.dtype.kind == "S":
            columns[name] = [raw.decode("utf-8").rstrip("\x00") for raw in values]
        else:
            columns[name] = values
    return pd.DataFrame(columns)


def _read_primaries(primaries_path: Path) -> pd.DataFrame:
    """Read primaries.bin into a table with one row per primary particle."""

    record_count = validate_binary_header(primaries_path, PRIMARY_DTYPE)
    records = np.fromfile(
        primaries_path,
        dtype=PRIMARY_DTYPE,
        count=record_count,
        offset=HEADER_SIZE,
    )
    return _table_from_records(records)


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

    Running this step again on the same run reproduces the same event times; a
    different run or sub-run gets a different set.
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


def _event_time_for_each_row(
    event_id: np.ndarray,
    event_times_ns: np.ndarray,
    binary_path: Path,
) -> np.ndarray:
    """Return the time in the run for every row, looked up by its event id."""

    if not len(event_id):
        return np.zeros(0, dtype=np.float64)
    if int(event_id.min()) < 0:
        raise ValueError(
            f"{binary_path.name} holds a row with no event id, so it cannot be "
            "placed on the run clock."
        )
    if int(event_id.max()) >= len(event_times_ns):
        raise ValueError(
            f"{binary_path.name} holds event {int(event_id.max())}, but the "
            f"configuration fired only {len(event_times_ns)} events. The "
            "configuration does not describe this run."
        )
    return event_times_ns[event_id]


def _binary_path(directory: str | None, filename: str) -> Path | None:
    """Return the binary file for a stage, or None when the stage has no output."""

    if not directory:
        return None
    path = Path(directory) / filename
    return path if path.exists() else None


def _write_primaries_table(config: Simulation, event_times_ns: np.ndarray) -> None:
    """Write primaries.parquet with interaction times on the run clock."""

    run_environment = config.metadata.run_environment
    binary_path = _binary_path(
        run_environment.primaries_directory,
        run_environment.primaries_filename,
    )
    if binary_path is None:
        return

    table = _read_primaries(binary_path)
    event_time_ns = _event_time_for_each_row(
        table["gun_call_id"].to_numpy(),
        event_times_ns,
        binary_path,
    )
    table["event_time_ns"] = event_time_ns
    # A primary that never interacted has no interaction time recorded, and
    # adding a time to that leaves it just as empty.
    table["primary_interaction_time_ns"] += event_time_ns

    output_path = binary_path.with_suffix(".parquet")
    table.to_parquet(output_path, index=False)
    logger.info("Wrote {} primaries to {}", len(table), output_path)


def _write_simulated_photons_table(
    config: Simulation,
    event_times_ns: np.ndarray,
) -> None:
    """Write simulatedPhotons/photons.parquet with times on the run clock."""

    run_environment = config.metadata.run_environment
    binary_path = _binary_path(
        run_environment.simulated_photons_directory,
        run_environment.photons_filename,
    )
    if binary_path is None:
        return

    table = _table_from_records(read_simulated_photons(binary_path))
    event_time_ns = _event_time_for_each_row(
        table["gun_call_id"].to_numpy(),
        event_times_ns,
        binary_path,
    )
    table["event_time_ns"] = event_time_ns
    table["photon_creation_time_ns"] += event_time_ns
    table["optical_interface_hit_time_ns"] += event_time_ns

    output_path = binary_path.with_suffix(".parquet")
    table.to_parquet(output_path, index=False)
    logger.info("Wrote {} simulated photons to {}", len(table), output_path)


def _write_photon_table(config: Simulation, event_times_ns: np.ndarray) -> None:
    """Write the HERMES photon table with arrival times on the run clock."""

    run_environment = config.metadata.run_environment
    binary_path = _binary_path(
        run_environment.transported_photons_directory,
        run_environment.photons_filename,
    )
    if binary_path is None:
        return

    photons = read_transported_photons(binary_path)
    cluster_id = photons["gun_call_id"]
    event_time_ns = _event_time_for_each_row(cluster_id, event_times_ns, binary_path)

    photon_table = pd.DataFrame(
        {
            "photon_id": np.arange(len(photons), dtype=np.uint64),
            "x": photons["photocathode_hit_x_mm"].astype(np.float64),
            "y": photons["photocathode_hit_y_mm"].astype(np.float64),
            "timestamp_canonical": (
                event_time_ns + photons["photocathode_hit_time_ns"]
            )
            / CANONICAL_TICK_NS,
            "tot": np.zeros(len(photons), dtype=np.uint64),
            "quality_flags": np.zeros(len(photons), dtype=np.uint16),
            "cluster_id": cluster_id,
            "primary_track_id": photons["primary_track_id"],
            "secondary_track_id": photons["secondary_track_id"],
            "event_time_ns": event_time_ns,
        }
    )

    # Label each photon with the species of the incident particle that caused it.
    primaries_path = _binary_path(
        run_environment.primaries_directory,
        run_environment.primaries_filename,
    )
    if primaries_path is None:
        raise FileNotFoundError(
            "The photon table needs the primaries table to label each photon with "
            "the incident particle that caused it, but no primaries file was found."
        )
    primary_species = _read_primaries(primaries_path)[
        ["gun_call_id", "primary_track_id", "primary_species"]
    ].rename(columns={"gun_call_id": "cluster_id", "primary_species": "event_type"})

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

    output_path = Path(run_environment.run_directory) / PHOTON_TABLE_FILENAME
    labeled.to_parquet(output_path, index=False)
    logger.info("Wrote {} photons to {}", len(labeled), output_path)


def write_parquet_tables(config: Simulation) -> None:
    """Write every finished stage's table with its times on the run clock.

    Each stage whose binary file is present gets a parquet copy alongside it,
    except the transported photons, whose table goes to the top of the run
    directory because that is the table HERMES reads. A stage that produced no
    binary file is skipped.
    """

    event_times_ns = _event_times_ns(config)
    timing_mode = "none" if config.source.timing is None else config.source.timing.mode
    logger.info(
        "Placing {} events on the run clock with '{}' source timing",
        len(event_times_ns),
        timing_mode,
    )

    _write_primaries_table(config, event_times_ns)
    _write_simulated_photons_table(config, event_times_ns)
    _write_photon_table(config, event_times_ns)
