"""Binary input and output for optical photon transport."""

import struct
from pathlib import Path

import numpy as np


HEADER_SIZE = 64
HEADER_VERSION = 1
HEADER_MAGIC = b"SCINPIX\x00"
HEADER_STRUCT = struct.Struct("<8sIIQ40s")

SIMULATED_PHOTON_DTYPE = np.dtype(
    [
        ("gun_call_id", "<i8"),
        ("primary_track_id", "<i4"),
        ("secondary_track_id", "<i4"),
        ("photon_track_id", "<i4"),
        ("_padding0", "V4"),
        ("photon_creation_time_ns", "<f8"),
        ("photon_origin_x_mm", "<f8"),
        ("photon_origin_y_mm", "<f8"),
        ("photon_origin_z_mm", "<f8"),
        ("photon_scint_exit_x_mm", "<f8"),
        ("photon_scint_exit_y_mm", "<f8"),
        ("photon_scint_exit_z_mm", "<f8"),
        ("optical_interface_hit_x_mm", "<f8"),
        ("optical_interface_hit_y_mm", "<f8"),
        ("optical_interface_hit_time_ns", "<f8"),
        ("optical_interface_hit_dir_x", "<f8"),
        ("optical_interface_hit_dir_y", "<f8"),
        ("optical_interface_hit_dir_z", "<f8"),
        ("optical_interface_hit_pol_x", "<f8"),
        ("optical_interface_hit_pol_y", "<f8"),
        ("optical_interface_hit_pol_z", "<f8"),
        ("optical_interface_hit_energy_eV", "<f8"),
        ("optical_interface_hit_wavelength_nm", "<f8"),
    ]
)

TRANSPORTED_PHOTON_DTYPE = np.dtype(
    [
        ("source_photon_index", "<i8"),
        ("gun_call_id", "<i8"),
        ("primary_track_id", "<i4"),
        ("secondary_track_id", "<i4"),
        ("photon_track_id", "<i4"),
        ("_padding0", "V4"),
        ("photocathode_hit_x_mm", "<f8"),
        ("photocathode_hit_y_mm", "<f8"),
        ("photocathode_hit_z_mm", "<f8"),
        ("photocathode_hit_time_ns", "<f8"),
        ("photocathode_hit_wavelength_nm", "<f8"),
    ]
)


def validate_binary_header(file_path: str | Path, dtype: np.dtype) -> int:
    """Validate a SCINPIX header and return the payload record count."""

    path = Path(file_path)
    with path.open("rb") as handle:
        header = handle.read(HEADER_SIZE)

    if len(header) != HEADER_SIZE:
        raise ValueError(f"SCINPIX header must be {HEADER_SIZE} bytes: {path}")

    magic, version, record_size, declared_count, padding = HEADER_STRUCT.unpack(header)
    if magic != HEADER_MAGIC:
        raise ValueError(f"Invalid SCINPIX magic in {path}: {magic!r}")
    if version != HEADER_VERSION:
        raise ValueError(f"Unsupported SCINPIX version in {path}: {version}")
    if record_size != dtype.itemsize:
        raise ValueError(
            f"SCINPIX record size mismatch in {path}: "
            f"header={record_size}, expected={dtype.itemsize}"
        )
    if padding != bytes(40):
        raise ValueError(f"SCINPIX reserved header bytes are not zero in {path}")

    payload_size = path.stat().st_size - HEADER_SIZE
    if payload_size % record_size:
        raise ValueError(f"SCINPIX payload is not a whole number of records: {path}")

    record_count = payload_size // record_size
    if declared_count not in (0, record_count):
        raise ValueError(
            f"SCINPIX record count mismatch in {path}: "
            f"header={declared_count}, payload={record_count}"
        )
    return record_count


def read_simulated_photons(file_path: str | Path) -> np.ndarray:
    """Read ``simulatedPhotons/photons.bin`` into a structured array."""

    record_count = validate_binary_header(file_path, SIMULATED_PHOTON_DTYPE)
    return np.fromfile(
        file_path,
        dtype=SIMULATED_PHOTON_DTYPE,
        count=record_count,
        offset=HEADER_SIZE,
    )


def read_transported_photons(file_path: str | Path) -> np.ndarray:
    """Read transported photocathode hits into a structured array."""

    record_count = validate_binary_header(file_path, TRANSPORTED_PHOTON_DTYPE)
    return np.fromfile(
        file_path,
        dtype=TRANSPORTED_PHOTON_DTYPE,
        count=record_count,
        offset=HEADER_SIZE,
    )


def write_transported_photons(
    file_path: str | Path,
    photons: np.ndarray,
) -> None:
    """Write transported photocathode hits with a SCINPIX header."""

    if photons.ndim != 1 or photons.dtype != TRANSPORTED_PHOTON_DTYPE:
        raise TypeError("photons must use TRANSPORTED_PHOTON_DTYPE")

    path = Path(file_path)
    header = HEADER_STRUCT.pack(
        HEADER_MAGIC,
        HEADER_VERSION,
        TRANSPORTED_PHOTON_DTYPE.itemsize,
        len(photons),
        bytes(40),
    )
    with path.open("wb") as handle:
        handle.write(header)
        photons.tofile(handle)
