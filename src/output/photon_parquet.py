"""Write a HERMES-style photon parquet file with ground-truth labels.

HERMES writes one parquet row per detected optical photon. This module produces
the same photon table from a finished ScintiPix run and adds truth columns that
record which incident particle caused each photon, so photon-clustering
algorithms can be tested against known ground truth.

The photon table columns match HERMES exactly:

    photon_id, x, y, timestamp_canonical, tot, quality_flags

and the truth columns added here are:

    cluster_id, primary_track_id, secondary_track_id, event_type

`tot` and `quality_flags` are placeholders (0): the intensifier and sensor
stages that would fill them are not implemented yet. The columns are present so
downstream HERMES code reads the same schema.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from src.optics.io import (
    HEADER_SIZE,
    read_transported_photons,
    validate_binary_header,
)

# One HERMES canonical time tick is 25 ns / 12288 (about 2.0345 ps). A photon
# time in nanoseconds is divided by this to get the canonical tick count.
CANONICAL_TICK_NS = 25.0 / 12288.0

# Conventional locations inside a run directory (see WorkingDirectoryLayout).
TRANSPORTED_PHOTONS_PATH = Path("transportedPhotons") / "photons.bin"
PRIMARIES_PATH = Path("primaries") / "primaries.bin"

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


def write_photon_parquet(run_directory: str | Path) -> Path:
    """Write ``photons.parquet`` for a finished run and return its path.

    Reads the transported photons and primaries from their conventional
    locations in ``run_directory``, labels each photon with the incident
    particle that caused it, and writes the HERMES-style photon table plus truth
    columns to ``run_directory/photons.parquet``.
    """

    run_directory = Path(run_directory)
    transported_path = run_directory / TRANSPORTED_PHOTONS_PATH
    primaries_path = run_directory / PRIMARIES_PATH

    photons = read_transported_photons(transported_path)
    primary_species = _read_primary_species(primaries_path)

    photon_table = pd.DataFrame(
        {
            "photon_id": np.arange(len(photons), dtype=np.uint64),
            "x": photons["photocathode_hit_x_mm"].astype(np.float64),
            "y": photons["photocathode_hit_y_mm"].astype(np.float64),
            "timestamp_canonical": photons["photocathode_hit_time_ns"]
            / CANONICAL_TICK_NS,
            "tot": np.zeros(len(photons), dtype=np.uint64),
            "quality_flags": np.zeros(len(photons), dtype=np.uint16),
            "cluster_id": photons["gun_call_id"],
            "primary_track_id": photons["primary_track_id"],
            "secondary_track_id": photons["secondary_track_id"],
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

    output_path = run_directory / OUTPUT_FILENAME
    labeled.to_parquet(output_path, index=False)
    logger.info("Wrote {} photons to {}", len(labeled), output_path)
    return output_path
