"""Tests for RayOptics photon transport."""

from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from src.config.yaml import from_yaml
from src.optics import raytrace
from src.optics.io import (
    HEADER_MAGIC,
    HEADER_STRUCT,
    HEADER_VERSION,
    SIMULATED_PHOTON_DTYPE,
    read_transported_photons,
)


def test_trace_photons_keeps_only_photocathode_hits(monkeypatch) -> None:
    config = from_yaml("examples/yamlFiles/EJ200_siemens_50mm.yaml")
    photons = np.zeros(4, dtype=SIMULATED_PHOTON_DTYPE)
    photons["gun_call_id"] = [10, 11, 12, 13]
    photons["primary_track_id"] = 20
    photons["secondary_track_id"] = 30
    photons["photon_track_id"] = [40, 41, 42, 43]
    photons["photon_scint_exit_x_mm"] = [1.0, 2.0, 3.0, np.nan]
    photons["photon_scint_exit_y_mm"] = 0.0
    photons["optical_interface_hit_dir_z"] = 1.0
    photons["optical_interface_hit_time_ns"] = 5.0
    photons["optical_interface_hit_wavelength_nm"] = 500.0
    image_points = iter(([2.0, 3.0, 0.0], [20.0, 0.0, 0.0]))
    traced_wavelengths = []

    def fake_trace(seq_model, point, direction, wavelength_nm, **kwargs):
        traced_wavelengths.append(wavelength_nm)
        if point[0] == 3.0:
            raise raytrace.TraceError()
        return SimpleNamespace(ray=[(next(image_points),)], op=250.0)

    monkeypatch.setattr(raytrace.trace, "trace", fake_trace)
    opt_model = {
        "seq_model": SimpleNamespace(
            gaps=[SimpleNamespace(thi=200.0)],
            wvlns=[486.0, 587.0],
        )
    }

    result = raytrace.trace_photons(config, opt_model, photons)

    assert len(result) == 1
    assert result["source_photon_index"].tolist() == [0]
    assert result["gun_call_id"].tolist() == [10]
    assert result["photon_track_id"].tolist() == [40]
    assert result["photocathode_hit_x_mm"].tolist() == [2.0]
    assert result["photocathode_hit_y_mm"].tolist() == [3.0]
    assert result["photocathode_hit_time_ns"][0] > 5.0
    assert traced_wavelengths == [486.0, 486.0, 486.0]
    assert result["photocathode_hit_wavelength_nm"].tolist() == [500.0]


def test_trace_photons_preserves_global_source_index(monkeypatch) -> None:
    config = from_yaml("examples/yamlFiles/EJ200_siemens_50mm.yaml")
    photons = np.zeros(4, dtype=SIMULATED_PHOTON_DTYPE)
    photons["optical_interface_hit_dir_z"] = 1.0
    photons["optical_interface_hit_wavelength_nm"] = 500.0

    monkeypatch.setattr(
        raytrace.trace,
        "trace",
        lambda *args, **kwargs: SimpleNamespace(ray=[([0.0, 0.0, 0.0],)], op=250.0),
    )
    opt_model = {
        "seq_model": SimpleNamespace(
            gaps=[SimpleNamespace(thi=200.0)],
            wvlns=[486.0],
        )
    }

    first_chunk = raytrace.trace_photons(
        config,
        opt_model,
        photons[:2],
        source_index_start=20,
    )
    second_chunk = raytrace.trace_photons(
        config,
        opt_model,
        photons[2:],
        source_index_start=22,
    )

    assert first_chunk["source_photon_index"].tolist() == [20, 21]
    assert second_chunk["source_photon_index"].tolist() == [22, 23]


def test_transport_photons_uses_simulation_paths(tmp_path, monkeypatch) -> None:
    config = from_yaml("examples/yamlFiles/EJ200_siemens_50mm.yaml")
    environment = config.metadata.run_environment
    environment.simulated_photons_directory = str(tmp_path / "simulatedPhotons")
    environment.transported_photons_directory = str(tmp_path / "transportedPhotons")
    Path(environment.simulated_photons_directory).mkdir()
    Path(environment.transported_photons_directory).mkdir()

    photons = np.zeros(1, dtype=SIMULATED_PHOTON_DTYPE)
    photons["photon_scint_exit_x_mm"] = 0.0
    photons["photon_scint_exit_y_mm"] = 0.0
    photons["optical_interface_hit_dir_z"] = 1.0
    photons["optical_interface_hit_wavelength_nm"] = 500.0
    input_path = Path(environment.simulated_photons_directory) / "photons.bin"
    input_path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            SIMULATED_PHOTON_DTYPE.itemsize,
            1,
            bytes(40),
        )
        + photons.tobytes()
    )
    monkeypatch.setattr(raytrace, "load_lens_model", lambda config: object())
    expected = np.zeros(1, dtype=raytrace.TRANSPORTED_PHOTON_DTYPE)
    expected["photon_track_id"] = 99
    monkeypatch.setattr(
        raytrace,
        "trace_photons",
        lambda config, opt_model, photons, source_index_start=0: expected,
    )

    output_path = raytrace.transport_photons(config)

    assert output_path == tmp_path / "transportedPhotons" / "photons.bin"
    assert read_transported_photons(output_path)["photon_track_id"].tolist() == [99]


def test_transport_photons_submits_contiguous_ranges_in_order(
    tmp_path,
    monkeypatch,
) -> None:
    config = from_yaml("examples/yamlFiles/EJ200_siemens_50mm.yaml")
    environment = config.metadata.run_environment
    environment.simulated_photons_directory = str(tmp_path / "simulatedPhotons")
    environment.transported_photons_directory = str(tmp_path / "transportedPhotons")
    Path(environment.simulated_photons_directory).mkdir()

    photons = np.zeros(2, dtype=SIMULATED_PHOTON_DTYPE)
    input_path = Path(environment.simulated_photons_directory) / "photons.bin"
    input_path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            SIMULATED_PHOTON_DTYPE.itemsize,
            2,
            bytes(40),
        )
        + photons.tobytes()
    )
    submitted_ranges = []
    executor_arguments = {}

    class FakeFuture:
        def __init__(self, result) -> None:
            self._result = result

        def result(self):
            return self._result

    class FakeExecutor:
        def __init__(self, **kwargs) -> None:
            executor_arguments.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            pass

        def submit(self, function, photon_range):
            submitted_ranges.append(photon_range)
            result = np.zeros(
                0 if photon_range == (0, 1) else 1,
                dtype=raytrace.TRANSPORTED_PHOTON_DTYPE,
            )
            if len(result):
                result["source_photon_index"] = photon_range[0]
            return FakeFuture(result)

    monkeypatch.setattr(raytrace, "_PHOTONS_PER_CHUNK", 1)
    monkeypatch.setattr(raytrace.os, "cpu_count", lambda: 2)
    monkeypatch.setattr(raytrace, "ProcessPoolExecutor", FakeExecutor)

    output_path = raytrace.transport_photons(config)

    assert executor_arguments == {
        "max_workers": 2,
        "initializer": raytrace._initialize_worker,
        "initargs": (config, input_path),
    }
    assert submitted_ranges == [(0, 1), (1, 2)]
    result = read_transported_photons(output_path)
    assert result["source_photon_index"].tolist() == [1]


def test_parallel_ranges_merge_in_order_after_reverse_completion(monkeypatch) -> None:
    first_result = np.zeros(1, dtype=raytrace.TRANSPORTED_PHOTON_DTYPE)
    first_result["source_photon_index"] = 0
    second_result = np.zeros(1, dtype=raytrace.TRANSPORTED_PHOTON_DTYPE)
    second_result["source_photon_index"] = 1
    futures = [Future(), Future()]
    completion_order = []
    submitted_ranges = []

    class FakeExecutor:
        def __init__(self, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            pass

        def submit(self, function, photon_range):
            future = futures[len(submitted_ranges)]
            submitted_ranges.append(photon_range)
            if photon_range == (1, 2):
                futures[1].set_result(second_result)
                completion_order.append(1)
                futures[0].set_result(first_result)
                completion_order.append(0)
            return future

    monkeypatch.setattr(raytrace, "ProcessPoolExecutor", FakeExecutor)

    chunks = list(
        raytrace._trace_ranges_parallel(
            object(),
            Path("photons.bin"),
            [(0, 1), (1, 2)],
            worker_count=2,
        )
    )

    assert submitted_ranges == [(0, 1), (1, 2)]
    assert completion_order == [1, 0]
    assert [chunk["source_photon_index"].tolist() for chunk in chunks] == [[0], [1]]


def test_transport_photons_uses_single_process_for_one_cpu(
    tmp_path,
    monkeypatch,
) -> None:
    config = from_yaml("examples/yamlFiles/EJ200_siemens_50mm.yaml")
    environment = config.metadata.run_environment
    environment.simulated_photons_directory = str(tmp_path / "simulatedPhotons")
    environment.transported_photons_directory = str(tmp_path / "transportedPhotons")
    Path(environment.simulated_photons_directory).mkdir()

    photons = np.zeros(3, dtype=SIMULATED_PHOTON_DTYPE)
    input_path = Path(environment.simulated_photons_directory) / "photons.bin"
    input_path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            SIMULATED_PHOTON_DTYPE.itemsize,
            3,
            bytes(40),
        )
        + photons.tobytes()
    )
    traced_ranges = []
    loaded_models = []

    def fake_load_lens_model(config):
        loaded_models.append(config)
        return object()

    def fake_trace_photons(config, opt_model, photons, source_index_start=0):
        traced_ranges.append((source_index_start, len(photons)))
        result = np.zeros(len(photons), dtype=raytrace.TRANSPORTED_PHOTON_DTYPE)
        result["source_photon_index"] = np.arange(
            source_index_start,
            source_index_start + len(photons),
        )
        return result

    monkeypatch.setattr(raytrace, "_PHOTONS_PER_CHUNK", 2)
    monkeypatch.setattr(raytrace.os, "cpu_count", lambda: 1)
    monkeypatch.setattr(raytrace, "load_lens_model", fake_load_lens_model)
    monkeypatch.setattr(raytrace, "trace_photons", fake_trace_photons)
    monkeypatch.setattr(
        raytrace,
        "ProcessPoolExecutor",
        lambda **kwargs: pytest.fail("single-core path started a process pool"),
    )

    output_path = raytrace.transport_photons(config)

    assert loaded_models == [config]
    assert traced_ranges == [(0, 2), (2, 1)]
    result = read_transported_photons(output_path)
    assert result["source_photon_index"].tolist() == [0, 1, 2]


def test_worker_initializes_its_own_memmap_and_lens(monkeypatch) -> None:
    config = from_yaml("examples/yamlFiles/EJ200_siemens_50mm.yaml")
    input_path = Path("simulatedPhotons/photons.bin")
    photons = np.zeros(4, dtype=SIMULATED_PHOTON_DTYPE)
    opt_model = object()
    traced = {}

    monkeypatch.setattr(raytrace, "_worker_config", None)
    monkeypatch.setattr(raytrace, "_worker_opt_model", None)
    monkeypatch.setattr(raytrace, "_worker_photons", None)
    monkeypatch.setattr(
        raytrace,
        "memory_map_simulated_photons",
        lambda path: photons if path == input_path else pytest.fail("wrong input path"),
    )
    monkeypatch.setattr(
        raytrace,
        "load_lens_model",
        lambda worker_config: (
            opt_model
            if worker_config is config
            else pytest.fail("wrong worker config")
        ),
    )

    raytrace._initialize_worker(config, input_path)

    def fake_trace_photons(
        worker_config,
        worker_opt_model,
        worker_photons,
        source_index_start=0,
    ):
        traced.update(
            config=worker_config,
            opt_model=worker_opt_model,
            photons=worker_photons,
            source_index_start=source_index_start,
        )
        return np.empty(0, dtype=raytrace.TRANSPORTED_PHOTON_DTYPE)

    monkeypatch.setattr(raytrace, "trace_photons", fake_trace_photons)
    result = raytrace._trace_photon_range((1, 3))

    assert traced["config"] is config
    assert traced["opt_model"] is opt_model
    assert np.shares_memory(traced["photons"], photons)
    assert len(traced["photons"]) == 2
    assert traced["source_index_start"] == 1
    assert len(result) == 0


def test_load_lens_model_requires_focused_back_focus() -> None:
    config = from_yaml("examples/yamlFiles/CanonEF50mmf1p0L_example.yaml")

    with pytest.raises(ValueError, match="backFocusMm"):
        raytrace.load_lens_model(config)
