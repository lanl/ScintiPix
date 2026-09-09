"""Tests for the per-stage parquet tables and the run clock they share."""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config.yaml import from_yaml
from src.models.source import SourceTiming
from src.optics.io import (
    HEADER_MAGIC,
    HEADER_STRUCT,
    HEADER_VERSION,
    SIMULATED_PHOTON_DTYPE,
    TRANSPORTED_PHOTON_DTYPE,
    write_transported_photons,
)
from src.output.parquet import (
    CANONICAL_TICK_NS,
    PRIMARY_DTYPE,
    _event_times_ns,
    write_parquet_tables,
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


def _config(tmp_path, timing: SourceTiming | None, event_count: int):
    """Build a run configuration whose stage directories live under `tmp_path`."""

    config = from_yaml(EXAMPLE_YAML)
    config.source.timing = timing
    config.geant4runner.number_of_particles = event_count

    run_environment = config.metadata.run_environment
    run_environment.simulation_run_id = "parquet_test"
    run_environment.working_directory = str(tmp_path)
    run_directory = run_environment.run_directory
    run_environment.primaries_directory = str(run_directory / "primaries")
    run_environment.simulated_photons_directory = str(
        run_directory / "simulatedPhotons"
    )
    run_environment.transported_photons_directory = str(
        run_directory / "transportedPhotons"
    )
    run_directory.mkdir(parents=True, exist_ok=True)
    return config


def _write_binary(path: Path, records: np.ndarray, dtype: np.dtype) -> None:
    """Write one binary table with a SCINPIX header, the way the simulation does."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            dtype.itemsize,
            len(records),
            bytes(40),
        )
        + records.tobytes()
    )


def _write_primaries(config, primaries: np.ndarray) -> Path:
    path = Path(config.metadata.run_environment.primaries_directory) / "primaries.bin"
    _write_binary(path, primaries, PRIMARY_DTYPE)
    return path


def _write_simulated_photons(config, photons: np.ndarray) -> Path:
    path = (
        Path(config.metadata.run_environment.simulated_photons_directory)
        / "photons.bin"
    )
    _write_binary(path, photons, SIMULATED_PHOTON_DTYPE)
    return path


def _write_transported_photons(config, photons: np.ndarray) -> Path:
    path = (
        Path(config.metadata.run_environment.transported_photons_directory)
        / "photons.bin"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    write_transported_photons(path, photons)
    return path


def _continuous_timing(start_time_ns: float = 0.0) -> SourceTiming:
    return SourceTiming(
        mode="continuous",
        start_time_ns=start_time_ns,
        particle_flux=FLUX_FOR_ONE_MILLION_PER_SECOND,
    )


def _two_neutron_primaries() -> np.ndarray:
    primaries = np.zeros(2, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10, 11]
    primaries["primary_track_id"] = [1, 1]
    primaries["primary_species"] = [b"neutron", b"neutron"]
    return primaries


def test_photon_table_labels_each_photon(tmp_path) -> None:
    config = _config(tmp_path, None, event_count=20)

    photons = np.zeros(3, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [10, 11, 10]
    photons["primary_track_id"] = [1, 1, 1]
    photons["secondary_track_id"] = [5, 7, 6]
    photons["photocathode_hit_x_mm"] = [1.0, -3.0, 0.5]
    photons["photocathode_hit_y_mm"] = [2.0, 4.0, -1.0]
    photons["photocathode_hit_time_ns"] = [25.0, 50.0, 12.5]
    _write_transported_photons(config, photons)

    primaries = _two_neutron_primaries()
    primaries["primary_species"] = [b"neutron", b"gamma"]
    _write_primaries(config, primaries)

    write_parquet_tables(config)

    output_path = config.metadata.run_environment.run_directory / "photons.parquet"
    table = pd.read_parquet(output_path)

    # The six HERMES columns, then the event id and the event type. Nothing else.
    assert list(table.columns) == [
        "photon_id",
        "x",
        "y",
        "timestamp_canonical",
        "tot",
        "quality_flags",
        "event_id",
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
    assert table["event_id"].tolist() == [10, 11, 10]
    assert (table["tot"] == 0).all()
    assert (table["quality_flags"] == 0).all()

    # Without a timing block every event stays at zero, so the recorded arrival
    # times are converted straight to ticks.
    expected_ticks = np.array([25.0, 50.0, 12.5]) / CANONICAL_TICK_NS
    np.testing.assert_allclose(table["timestamp_canonical"].to_numpy(), expected_ticks)

    assert table["event_type"].tolist() == ["neutron", "gamma", "neutron"]


def test_two_incident_particles_in_one_firing_share_an_event_id(tmp_path) -> None:
    """A neutron and its coincident gamma are told apart by `event_type` alone.

    Both belong to the same firing, so they share one `event_id`. The table no
    longer says which incident particle each photon came from, so the labelling
    has to survive being matched on a track id that is not written out.
    """

    config = _config(tmp_path, None, event_count=20)

    photons = np.zeros(3, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [10, 10, 10]
    photons["primary_track_id"] = [1, 2, 1]
    _write_transported_photons(config, photons)

    primaries = np.zeros(2, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10, 10]
    primaries["primary_track_id"] = [1, 2]
    primaries["primary_species"] = [b"neutron", b"gamma"]
    _write_primaries(config, primaries)

    write_parquet_tables(config)

    table = pd.read_parquet(
        config.metadata.run_environment.run_directory / "photons.parquet"
    )

    assert len(table) == 3
    assert table["event_id"].tolist() == [10, 10, 10]
    assert table["event_type"].tolist() == ["neutron", "gamma", "neutron"]


def test_photon_table_leaves_unmatched_event_type_empty(tmp_path) -> None:
    config = _config(tmp_path, None, event_count=100)

    photons = np.zeros(1, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [99]
    photons["primary_track_id"] = [1]
    _write_transported_photons(config, photons)

    primaries = np.zeros(1, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10]
    primaries["primary_track_id"] = [1]
    primaries["primary_species"] = [b"neutron"]
    _write_primaries(config, primaries)

    write_parquet_tables(config)

    table = pd.read_parquet(
        config.metadata.run_environment.run_directory / "photons.parquet"
    )
    assert table["event_type"].tolist() == [""]


def test_photon_times_shift_with_their_own_event(tmp_path) -> None:
    """Every photon in one event moves by the same amount, keeping its spread."""

    config = _config(tmp_path, _continuous_timing(), event_count=200)

    photons = np.zeros(3, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["gun_call_id"] = [10, 11, 10]
    photons["primary_track_id"] = [1, 1, 1]
    photons["photocathode_hit_time_ns"] = [25.0, 50.0, 12.5]
    _write_transported_photons(config, photons)
    _write_primaries(config, _two_neutron_primaries())

    write_parquet_tables(config)

    table = pd.read_parquet(
        config.metadata.run_environment.run_directory / "photons.parquet"
    )

    # The photon table does not carry the event time, so look it up by event id.
    # The two photons from event 10 share one event time; event 11 gets its own.
    event_times = _event_times_ns(config)[table["event_id"].to_numpy()]
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


def test_primaries_table_shifts_interaction_times(tmp_path) -> None:
    """Each primary's interaction time moves onto the run clock."""

    config = _config(tmp_path, _continuous_timing(), event_count=200)

    primaries = np.zeros(3, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10, 11, 12]
    primaries["primary_track_id"] = [1, 1, 1]
    primaries["primary_species"] = [b"neutron", b"neutron", b"neutron"]
    # The last primary never interacted, so it has no interaction time.
    primaries["primary_interaction_time_ns"] = [3.0, 7.5, np.nan]
    _write_primaries(config, primaries)

    write_parquet_tables(config)

    table = pd.read_parquet(
        Path(config.metadata.run_environment.primaries_directory)
        / "primaries.parquet"
    )

    assert len(table) == 3
    assert "_padding0" not in table.columns
    assert table["gun_call_id"].tolist() == [10, 11, 12]
    assert table["primary_species"].tolist() == ["neutron", "neutron", "neutron"]

    event_times = table["event_time_ns"].to_numpy()
    assert (event_times > 0.0).all()
    assert len(set(event_times.tolist())) == 3

    np.testing.assert_allclose(
        table["primary_interaction_time_ns"].to_numpy()[:2],
        event_times[:2] + np.array([3.0, 7.5]),
    )
    # A primary with no interaction time still has none afterwards.
    assert math.isnan(table["primary_interaction_time_ns"].to_numpy()[2])


def test_simulated_photons_table_shifts_both_of_its_times(tmp_path) -> None:
    config = _config(tmp_path, _continuous_timing(), event_count=200)

    photons = np.zeros(2, dtype=SIMULATED_PHOTON_DTYPE)
    photons["gun_call_id"] = [10, 11]
    photons["primary_track_id"] = [1, 1]
    photons["photon_creation_time_ns"] = [1.5, 2.5]
    photons["optical_interface_hit_time_ns"] = [11.5, 22.5]
    _write_simulated_photons(config, photons)
    _write_primaries(config, _two_neutron_primaries())

    write_parquet_tables(config)

    table = pd.read_parquet(
        Path(config.metadata.run_environment.simulated_photons_directory)
        / "photons.parquet"
    )

    assert "_padding0" not in table.columns
    event_times = table["event_time_ns"].to_numpy()
    assert (event_times > 0.0).all()
    np.testing.assert_allclose(
        table["photon_creation_time_ns"].to_numpy(),
        event_times + np.array([1.5, 2.5]),
    )
    np.testing.assert_allclose(
        table["optical_interface_hit_time_ns"].to_numpy(),
        event_times + np.array([11.5, 22.5]),
    )


def test_tables_are_written_when_transport_did_not_run(tmp_path) -> None:
    """A run with transport disabled still gets its neutron times processed."""

    config = _config(tmp_path, _continuous_timing(), event_count=200)
    config.metadata.run_controls.transportation = False

    primaries = np.zeros(2, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10, 11]
    primaries["primary_track_id"] = [1, 1]
    primaries["primary_species"] = [b"neutron", b"neutron"]
    primaries["primary_interaction_time_ns"] = [3.0, 7.5]
    _write_primaries(config, primaries)

    simulated = np.zeros(1, dtype=SIMULATED_PHOTON_DTYPE)
    simulated["gun_call_id"] = [10]
    simulated["primary_track_id"] = [1]
    simulated["photon_creation_time_ns"] = [1.5]
    _write_simulated_photons(config, simulated)

    write_parquet_tables(config)

    run_directory = config.metadata.run_environment.run_directory
    primaries_table = pd.read_parquet(run_directory / "primaries" / "primaries.parquet")
    simulated_table = pd.read_parquet(
        run_directory / "simulatedPhotons" / "photons.parquet"
    )

    assert (primaries_table["event_time_ns"] > 0.0).all()
    assert (primaries_table["primary_interaction_time_ns"] > 100.0).all()
    assert (simulated_table["event_time_ns"] > 0.0).all()

    # No transported photons were written, so there is no photon table.
    assert not (run_directory / "photons.parquet").exists()


def test_a_stage_that_wrote_nothing_is_skipped(tmp_path) -> None:
    config = _config(tmp_path, None, event_count=10)

    primaries = np.zeros(1, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [0]
    primaries["primary_track_id"] = [1]
    primaries["primary_species"] = [b"neutron"]
    _write_primaries(config, primaries)

    write_parquet_tables(config)

    run_directory = config.metadata.run_environment.run_directory
    assert (run_directory / "primaries" / "primaries.parquet").exists()
    assert not (run_directory / "simulatedPhotons" / "photons.parquet").exists()
    assert not (run_directory / "photons.parquet").exists()


def test_the_binaries_are_left_on_their_own_clock(tmp_path) -> None:
    """The binaries keep the times Geant4 recorded, so the step can be repeated."""

    config = _config(tmp_path, _continuous_timing(), event_count=200)

    primaries = np.zeros(1, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [10]
    primaries["primary_track_id"] = [1]
    primaries["primary_species"] = [b"neutron"]
    primaries["primary_interaction_time_ns"] = [3.0]
    primaries_path = _write_primaries(config, primaries)
    before = primaries_path.read_bytes()

    write_parquet_tables(config)
    first = pd.read_parquet(
        Path(config.metadata.run_environment.primaries_directory)
        / "primaries.parquet"
    )

    assert primaries_path.read_bytes() == before

    # Running the step again gives exactly the same table rather than shifting twice.
    write_parquet_tables(config)
    second = pd.read_parquet(
        Path(config.metadata.run_environment.primaries_directory)
        / "primaries.parquet"
    )
    pd.testing.assert_frame_equal(first, second)


def test_writer_rejects_a_configuration_from_a_different_run(tmp_path) -> None:
    config = _config(tmp_path, None, event_count=10)

    primaries = np.zeros(1, dtype=PRIMARY_DTYPE)
    primaries["gun_call_id"] = [500]
    primaries["primary_track_id"] = [1]
    primaries["primary_species"] = [b"neutron"]
    _write_primaries(config, primaries)

    with pytest.raises(ValueError, match="fired only 10 events"):
        write_parquet_tables(config)


def test_event_times_are_all_zero_without_a_timing_block(tmp_path) -> None:
    times_ns = _event_times_ns(_config(tmp_path, None, event_count=50))

    assert len(times_ns) == 50
    assert (times_ns == 0.0).all()


def test_event_times_are_all_zero_in_none_mode(tmp_path) -> None:
    times_ns = _event_times_ns(
        _config(tmp_path, SourceTiming(mode="none"), event_count=50)
    )

    assert (times_ns == 0.0).all()


def test_continuous_event_times_match_the_configured_rate(tmp_path) -> None:
    event_count = 200_000
    times_ns = _event_times_ns(
        _config(
            tmp_path,
            _continuous_timing(start_time_ns=500.0),
            event_count=event_count,
        )
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


def test_pulsed_event_times_land_inside_the_pulse_windows(tmp_path) -> None:
    # 1,000,000 particles per second over a 1 ms pulse period is 1000 per pulse.
    timing = SourceTiming(
        mode="pulsed",
        start_time_ns=0.0,
        particle_flux=FLUX_FOR_ONE_MILLION_PER_SECOND,
        pulse_period_ns=1.0e6,
        pulse_time_offset_ns=0.0,
        pulse_time_width_ns=270.0,
    )
    times_ns = _event_times_ns(_config(tmp_path, timing, event_count=2500))

    pulse_index = np.arange(2500) // 1000
    window_start_ns = pulse_index * 1.0e6
    assert (times_ns >= window_start_ns).all()
    assert (times_ns <= window_start_ns + 270.0).all()

    # Three windows, holding 1000, 1000, and the remaining 500 events.
    counts = np.bincount(pulse_index)
    assert counts.tolist() == [1000, 1000, 500]


def test_event_times_repeat_for_the_same_run(tmp_path) -> None:
    """The same run always reproduces its own event times."""

    first = _event_times_ns(_config(tmp_path, _continuous_timing(), event_count=1000))
    second = _event_times_ns(_config(tmp_path, _continuous_timing(), event_count=1000))

    np.testing.assert_array_equal(first, second)


def test_event_times_differ_between_sub_runs(tmp_path) -> None:
    config = _config(tmp_path, _continuous_timing(), event_count=1000)
    first = _event_times_ns(config)

    config.metadata.run_environment.sub_run_number = 7
    second = _event_times_ns(config)

    assert not np.array_equal(first, second)
