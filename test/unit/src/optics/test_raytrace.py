"""Tests for RayOptics photon transport."""

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
    photons = np.zeros(3, dtype=SIMULATED_PHOTON_DTYPE)
    photons["gun_call_id"] = [10, 11, 12]
    photons["primary_track_id"] = 20
    photons["secondary_track_id"] = 30
    photons["photon_track_id"] = [40, 41, 42]
    photons["photon_scint_exit_x_mm"] = [1.0, 2.0, np.nan]
    photons["photon_scint_exit_y_mm"] = 0.0
    photons["optical_interface_hit_dir_z"] = 1.0
    photons["optical_interface_hit_time_ns"] = 5.0
    photons["optical_interface_hit_wavelength_nm"] = 500.0
    image_points = iter(([2.0, 3.0, 0.0], [20.0, 0.0, 0.0]))
    traced_wavelengths = []

    def fake_trace(seq_model, point, direction, wavelength_nm, **kwargs):
        traced_wavelengths.append(wavelength_nm)
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
    assert traced_wavelengths == [486.0, 486.0]
    assert result["photocathode_hit_wavelength_nm"].tolist() == [500.0]


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
        lambda config, opt_model, photons: expected,
    )

    output_path = raytrace.transport_photons(config)

    assert output_path == tmp_path / "transportedPhotons" / "photons.bin"
    assert read_transported_photons(output_path)["photon_track_id"].tolist() == [99]


def test_load_lens_model_requires_focused_back_focus() -> None:
    config = from_yaml("examples/yamlFiles/CanonEF50mmf1p0L_example.yaml")

    with pytest.raises(ValueError, match="backFocusMm"):
        raytrace.load_lens_model(config)
