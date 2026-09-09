"""Tests for the HERMES-style photon parquet export."""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config.yaml import from_yaml, write_yaml
from src.models.source import SourceTiming
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
    _event_times_ns,
    write_photon_parquet,
)

EXAMPLE_YAML = (
    Path(__file__).resolve().parents[4]
    / "examples"
    / "yamlFiles"
    / "CanonEF50mmf1p0L_example.yaml"
)

# The example source is a 10 mm radius disc, so its area is pi square centimetres
# and this flux makes the source fire 1,000,000 particles per second.
FLUX_FOR_ONE_MILLION_PER_SECOND = 1.0e6 / math.pi
MEAN_GAP_NS = 1000.0


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


def _config(timing: SourceTiming | None, event_count: int):
    """Build a run configuration with the given source timing and particle count."""

    config = from_yaml(EXAMPLE_YAML)
    config.source.timing = timing
    config.geant4runner.number_of_particles = event_count
    return config


def _write_config(run_directory, timing: SourceTiming | None, event_count: int) -> None:
    """Save a run configuration the way `run_simulation` does."""

    write_yaml(
        _config(timing, event_count),
        run_directory / "config" / "photon_parquet_test_000.yaml",
    )


def _continuous_timing(start_time_ns: float = 0.0) -> SourceTiming:
    return SourceTiming(
        mode="continuous",
        start_time_ns=start_time_ns,
        particle_flux=FLUX_FOR_ONE_MILLION_PER_SECOND,
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

    _write_config(tmp_path, None, event_count=20)

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
        "event_time_ns",
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

    # Without a timing block every event stays at zero, so the recorded arrival
    # times are converted straight to ticks.
    assert (table["event_time_ns"] == 0.0).all()
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

    _write_config(tmp_path, None, event_count=100)

    output_path = write_photon_parquet(tmp_path)
    table = pd.read_parquet(output_path)

    assert table["event_type"].tolist() == [""]


def test_photon_times_shift_with_their_own_event(tmp_path) -> None:
    """Every photon in one event moves by the same amount, keeping its spread."""

    photons = np.zeros(3, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [10, 11, 10]
    photons["primary_track_id"] = [1, 1, 1]
    photons["photocathode_hit_time_ns"] = [25.0, 50.0, 12.5]
    _write_transported(tmp_path, photons)

    primaries = np.zeros(2, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10, 11]
    primaries["primary_track_id"] = [1, 1]
    primaries["primary_species"] = [b"neutron", b"neutron"]
    _write_primaries(tmp_path, primaries)

    _write_config(tmp_path, _continuous_timing(), event_count=200)

    table = pd.read_parquet(write_photon_parquet(tmp_path))

    # The two photons from event 10 share one event time; event 11 gets its own.
    event_times = table["event_time_ns"].to_numpy()
    assert event_times[0] == event_times[2]
    assert event_times[1] != event_times[0]
    assert (event_times > 0.0).all()

    # Each timestamp is the event time plus the time Geant4 recorded.
    recorded_ns = np.array([25.0, 50.0, 12.5])
    np.testing.assert_allclose(
        table["timestamp_canonical"].to_numpy(),
        (event_times + recorded_ns) / CANONICAL_TICK_NS,
    )

    # The spread within event 10 is untouched by the shift.
    ticks = table["timestamp_canonical"].to_numpy()
    np.testing.assert_allclose(ticks[0] - ticks[2], (25.0 - 12.5) / CANONICAL_TICK_NS)


def test_writer_rejects_a_configuration_from_a_different_run(tmp_path) -> None:
    photons = np.zeros(1, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [500]
    photons["primary_track_id"] = [1]
    _write_transported(tmp_path, photons)

    primaries = np.zeros(1, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [500]
    primaries["primary_track_id"] = [1]
    primaries["primary_species"] = [b"neutron"]
    _write_primaries(tmp_path, primaries)

    _write_config(tmp_path, None, event_count=10)

    with pytest.raises(ValueError, match="fired only 10 events"):
        write_photon_parquet(tmp_path)


def test_writer_requires_a_saved_configuration(tmp_path) -> None:
    photons = np.zeros(1, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [0]
    photons["primary_track_id"] = [1]
    _write_transported(tmp_path, photons)

    primaries = np.zeros(1, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [0]
    primaries["primary_track_id"] = [1]
    primaries["primary_species"] = [b"neutron"]
    _write_primaries(tmp_path, primaries)

    with pytest.raises(FileNotFoundError, match="exactly one saved configuration"):
        write_photon_parquet(tmp_path)


def test_event_times_are_all_zero_without_a_timing_block() -> None:
    times_ns = _event_times_ns(_config(None, event_count=50))

    assert len(times_ns) == 50
    assert (times_ns == 0.0).all()


def test_event_times_are_all_zero_in_none_mode() -> None:
    times_ns = _event_times_ns(_config(SourceTiming(mode="none"), event_count=50))

    assert (times_ns == 0.0).all()


def test_continuous_event_times_match_the_configured_rate() -> None:
    event_count = 200_000
    times_ns = _event_times_ns(
        _config(_continuous_timing(start_time_ns=500.0), event_count=event_count)
    )

    assert len(times_ns) == event_count
    # Events arrive in order, and the first one lands after the start time.
    assert (np.diff(times_ns) > 0.0).all()
    assert times_ns[0] > 500.0

    # Random gaps average out to the spacing the configured rate implies.
    gaps_ns = np.diff(times_ns)
    assert MEAN_GAP_NS * 0.98 < gaps_ns.mean() < MEAN_GAP_NS * 1.02

    # The gaps are genuinely random rather than a fixed spacing.
    assert gaps_ns.std() > MEAN_GAP_NS * 0.5

    # The rate over the whole run matches too.
    elapsed_seconds = (times_ns[-1] - 500.0) / 1.0e9
    assert 0.98e6 < event_count / elapsed_seconds < 1.02e6


def test_pulsed_event_times_land_inside_the_pulse_windows() -> None:
    # 1,000,000 particles per second over a 1 ms pulse period is 1000 per pulse.
    timing = SourceTiming(
        mode="pulsed",
        start_time_ns=0.0,
        particle_flux=FLUX_FOR_ONE_MILLION_PER_SECOND,
        pulse_period_ns=1.0e6,
        pulse_time_offset_ns=0.0,
        pulse_time_width_ns=270.0,
    )
    times_ns = _event_times_ns(_config(timing, event_count=2500))

    pulse_index = np.arange(2500) // 1000
    window_start_ns = pulse_index * 1.0e6
    assert (times_ns >= window_start_ns).all()
    assert (times_ns <= window_start_ns + 270.0).all()

    # Three windows, holding 1000, 1000, and the remaining 500 events.
    counts = np.bincount(pulse_index)
    assert counts.tolist() == [1000, 1000, 500]


def test_event_times_repeat_for_the_same_run() -> None:
    """The same run directory always reproduces its own event times."""

    first = _event_times_ns(_config(_continuous_timing(), event_count=1000))
    second = _event_times_ns(_config(_continuous_timing(), event_count=1000))

    np.testing.assert_array_equal(first, second)


def test_event_times_differ_between_sub_runs() -> None:
    config = _config(_continuous_timing(), event_count=1000)
    first = _event_times_ns(config)

    config.metadata.run_environment.sub_run_number = 7
    second = _event_times_ns(config)

    assert not np.array_equal(first, second)
