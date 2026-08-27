"""Tests for the HERMES-style photon parquet export."""

import numpy as np
import pandas as pd

from src.optics.io import (
    HEADER_MAGIC,
    HEADER_STRUCT,
    HEADER_VERSION,
    TRANSPORTED_PHOTON_DTYPE,
    write_transported_photons,
)
from src.output.photon_parquet import (
    CANONICAL_TICK_NS,
    PRIMARY_DTYPE,
    write_photon_parquet,
)


def _write_transported(run_directory, photons: np.ndarray) -> None:
    path = run_directory / "transportedPhotons" / "photons.bin"
    path.parent.mkdir(parents=True)
    write_transported_photons(path, photons)


def _write_primaries(run_directory, primaries: np.ndarray) -> None:
    path = run_directory / "primaries" / "primaries.bin"
    path.parent.mkdir(parents=True)
    path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            PRIMARY_DTYPE.itemsize,
            len(primaries),
            bytes(40),
        )
        + primaries.tobytes()
    )


def test_write_photon_parquet_labels_each_photon(tmp_path) -> None:
    photons = np.zeros(3, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [10, 11, 10]
    photons["primary_track_id"] = [1, 1, 1]
    photons["secondary_track_id"] = [5, 7, 6]
    photons["photocathode_hit_x_mm"] = [1.0, -3.0, 0.5]
    photons["photocathode_hit_y_mm"] = [2.0, 4.0, -1.0]
    photons["photocathode_hit_time_ns"] = [25.0, 50.0, 12.5]
    _write_transported(tmp_path, photons)

    primaries = np.zeros(2, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10, 11]
    primaries["primary_track_id"] = [1, 1]
    primaries["primary_species"] = [b"neutron", b"gamma"]
    _write_primaries(tmp_path, primaries)

    output_path = write_photon_parquet(tmp_path)

    assert output_path == tmp_path / "photons.parquet"
    table = pd.read_parquet(output_path)

    assert list(table.columns) == [
        "photon_id",
        "x",
        "y",
        "timestamp_canonical",
        "tot",
        "quality_flags",
        "cluster_id",
        "primary_track_id",
        "secondary_track_id",
        "event_type",
    ]
    assert table["photon_id"].dtype == np.uint64
    assert table["tot"].dtype == np.uint64
    assert table["quality_flags"].dtype == np.uint16
    assert table["x"].dtype == np.float64
    assert table["timestamp_canonical"].dtype == np.float64

    assert table["photon_id"].tolist() == [0, 1, 2]
    assert table["x"].tolist() == [1.0, -3.0, 0.5]
    assert table["y"].tolist() == [2.0, 4.0, -1.0]
    assert table["cluster_id"].tolist() == [10, 11, 10]
    assert table["secondary_track_id"].tolist() == [5, 7, 6]
    assert (table["tot"] == 0).all()
    assert (table["quality_flags"] == 0).all()

    expected_ticks = np.array([25.0, 50.0, 12.5]) / CANONICAL_TICK_NS
    np.testing.assert_allclose(table["timestamp_canonical"].to_numpy(), expected_ticks)

    assert table["event_type"].tolist() == ["neutron", "gamma", "neutron"]


def test_write_photon_parquet_leaves_unmatched_event_type_empty(tmp_path) -> None:
    photons = np.zeros(1, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [99]
    photons["primary_track_id"] = [1]
    _write_transported(tmp_path, photons)

    primaries = np.zeros(1, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10]
    primaries["primary_track_id"] = [1]
    primaries["primary_species"] = [b"neutron"]
    _write_primaries(tmp_path, primaries)

    output_path = write_photon_parquet(tmp_path)
    table = pd.read_parquet(output_path)

    assert table["event_type"].tolist() == [""]
