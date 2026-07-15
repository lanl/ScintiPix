"""Tests for the optical-transport binary contract."""

import numpy as np
import pytest

from src.optics.io import (
    HEADER_MAGIC,
    HEADER_SIZE,
    HEADER_STRUCT,
    HEADER_VERSION,
    SIMULATED_PHOTON_DTYPE,
    TRANSPORTED_PHOTON_DTYPE,
    append_transported_photons,
    memory_map_simulated_photons,
    read_simulated_photons,
    read_transported_photons,
    validate_binary_header,
    write_transported_photon_header,
    write_transported_photons,
)


def test_simulated_photon_dtype_matches_geant4_layout() -> None:
    assert SIMULATED_PHOTON_DTYPE.itemsize == 168
    assert SIMULATED_PHOTON_DTYPE.fields["photon_creation_time_ns"][1] == 24
    assert SIMULATED_PHOTON_DTYPE.fields["optical_interface_hit_x_mm"][1] == 80
    assert SIMULATED_PHOTON_DTYPE.fields["optical_interface_hit_wavelength_nm"][1] == 160


def test_transported_photon_dtype_has_stable_layout() -> None:
    assert TRANSPORTED_PHOTON_DTYPE.itemsize == 72
    assert TRANSPORTED_PHOTON_DTYPE.fields["photocathode_hit_x_mm"][1] == 32
    assert TRANSPORTED_PHOTON_DTYPE.fields["photocathode_hit_wavelength_nm"][1] == 64


def test_read_simulated_photons(tmp_path) -> None:
    path = tmp_path / "simulatedPhotons" / "photons.bin"
    path.parent.mkdir()
    photons = np.zeros(1, dtype=SIMULATED_PHOTON_DTYPE)
    photons["gun_call_id"] = 12
    photons["photon_track_id"] = 34
    photons["optical_interface_hit_wavelength_nm"] = 450.0
    path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            SIMULATED_PHOTON_DTYPE.itemsize,
            0,
            bytes(40),
        )
        + photons.tobytes()
    )

    result = read_simulated_photons(path)

    assert result.dtype == SIMULATED_PHOTON_DTYPE
    assert result["gun_call_id"].tolist() == [12]
    assert result["photon_track_id"].tolist() == [34]
    assert result["optical_interface_hit_wavelength_nm"].tolist() == [450.0]


def test_memory_map_simulated_photons(tmp_path) -> None:
    path = tmp_path / "photons.bin"
    photons = np.zeros(2, dtype=SIMULATED_PHOTON_DTYPE)
    photons["photon_track_id"] = [34, 35]
    path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            SIMULATED_PHOTON_DTYPE.itemsize,
            2,
            bytes(40),
        )
        + photons.tobytes()
    )

    result = memory_map_simulated_photons(path)

    assert isinstance(result, np.memmap)
    assert result.dtype == SIMULATED_PHOTON_DTYPE
    assert result["photon_track_id"].tolist() == [34, 35]


@pytest.mark.parametrize(
    ("header", "message"),
    [
        (
            HEADER_STRUCT.pack(
                b"NOTPIX\x00\x00",
                HEADER_VERSION,
                SIMULATED_PHOTON_DTYPE.itemsize,
                0,
                bytes(40),
            ),
            "magic",
        ),
        (
            HEADER_STRUCT.pack(
                HEADER_MAGIC,
                2,
                SIMULATED_PHOTON_DTYPE.itemsize,
                0,
                bytes(40),
            ),
            "version",
        ),
        (
            HEADER_STRUCT.pack(
                HEADER_MAGIC,
                HEADER_VERSION,
                96,
                0,
                bytes(40),
            ),
            "record size",
        ),
    ],
)
def test_validate_binary_header_rejects_invalid_fields(
    tmp_path,
    header: bytes,
    message: str,
) -> None:
    path = tmp_path / "photons.bin"
    path.write_bytes(header)

    with pytest.raises(ValueError, match=message):
        validate_binary_header(path, SIMULATED_PHOTON_DTYPE)


def test_validate_binary_header_rejects_short_header(tmp_path) -> None:
    path = tmp_path / "photons.bin"
    path.write_bytes(bytes(HEADER_SIZE - 1))

    with pytest.raises(ValueError, match="must be 64 bytes"):
        validate_binary_header(path, SIMULATED_PHOTON_DTYPE)


def test_validate_binary_header_rejects_truncated_payload(tmp_path) -> None:
    path = tmp_path / "photons.bin"
    path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            SIMULATED_PHOTON_DTYPE.itemsize,
            0,
            bytes(40),
        )
        + bytes(SIMULATED_PHOTON_DTYPE.itemsize - 1)
    )

    with pytest.raises(ValueError, match="whole number"):
        validate_binary_header(path, SIMULATED_PHOTON_DTYPE)


def test_validate_binary_header_rejects_incorrect_record_count(tmp_path) -> None:
    path = tmp_path / "photons.bin"
    path.write_bytes(
        HEADER_STRUCT.pack(
            HEADER_MAGIC,
            HEADER_VERSION,
            SIMULATED_PHOTON_DTYPE.itemsize,
            2,
            bytes(40),
        )
        + bytes(SIMULATED_PHOTON_DTYPE.itemsize)
    )

    with pytest.raises(ValueError, match="record count mismatch"):
        validate_binary_header(path, SIMULATED_PHOTON_DTYPE)


def test_transported_photon_binary_round_trip(tmp_path) -> None:
    path = tmp_path / "photons.bin"
    photons = np.zeros(2, dtype=TRANSPORTED_PHOTON_DTYPE)
    photons["source_photon_index"] = [3, 8]
    photons["gun_call_id"] = [10, 11]
    photons["photon_track_id"] = [30, 31]
    photons["photocathode_hit_x_mm"] = [1.25, -2.5]
    photons["photocathode_hit_time_ns"] = [7.0, 8.0]
    photons["photocathode_hit_wavelength_nm"] = [420.0, 510.0]

    write_transported_photons(path, photons)
    result = read_transported_photons(path)

    assert path.stat().st_size == HEADER_SIZE + 2 * TRANSPORTED_PHOTON_DTYPE.itemsize
    assert result.dtype == TRANSPORTED_PHOTON_DTYPE
    np.testing.assert_array_equal(result, photons)
    _, _, record_size, record_count, _ = HEADER_STRUCT.unpack(
        path.read_bytes()[:HEADER_SIZE]
    )
    assert record_size == 72
    assert record_count == 2


def test_incremental_transported_photon_write(tmp_path) -> None:
    path = tmp_path / "photons.bin"
    first_chunk = np.zeros(2, dtype=TRANSPORTED_PHOTON_DTYPE)
    first_chunk["source_photon_index"] = [2, 4]
    second_chunk = np.zeros(1, dtype=TRANSPORTED_PHOTON_DTYPE)
    second_chunk["source_photon_index"] = 8

    with path.open("wb") as handle:
        write_transported_photon_header(handle, 0)
        append_transported_photons(handle, first_chunk)
        append_transported_photons(handle, second_chunk)
        write_transported_photon_header(handle, 3)

    result = read_transported_photons(path)

    assert result["source_photon_index"].tolist() == [2, 4, 8]
    _, _, _, record_count, _ = HEADER_STRUCT.unpack(path.read_bytes()[:HEADER_SIZE])
    assert record_count == 3
