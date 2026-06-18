"""
Read ScintiPix binary output files.

Binary format:
- 64-byte header: magic, version, record_size, record_count, padding
- Fixed-size records: array of struct data

Usage:
    import read_binary_output as reader
    df = reader.read_primaries("test_output/primaries.bin")
    df = reader.read_secondaries("test_output/secondaries.bin")
    df = reader.read_photons("test_output/photons.bin")
"""

import struct
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd


# Binary header structure (64 bytes)
HEADER_FORMAT = "8sII8x40x"  # magic(8), version(4), record_size(4), record_count(8), padding(40)
HEADER_SIZE = 64

# Record structures (match C++ structs)
PRIMARY_DTYPE = np.dtype([
    ("gun_call_id", np.int64),
    ("primary_track_id", np.int32),
    ("_padding1", "V4"),  # 4-byte padding for alignment
    ("primary_species", "S24"),  # Fixed 24-char string
    ("primary_x_mm", np.float64),
    ("primary_y_mm", np.float64),
    ("primary_energy_MeV", np.float64),
    ("primary_interaction_time_ns", np.float64),
    ("primary_created_secondary_count", np.int64),
    ("primary_generated_optical_photon_count", np.int64),
    ("primary_detected_optical_interface_photon_count", np.int64),
])

SECONDARY_DTYPE = np.dtype([
    ("gun_call_id", np.int64),
    ("primary_track_id", np.int32),
    ("secondary_track_id", np.int32),
    ("secondary_species", "S24"),
    ("secondary_origin_x_mm", np.float64),
    ("secondary_origin_y_mm", np.float64),
    ("secondary_origin_z_mm", np.float64),
    ("secondary_origin_energy_MeV", np.float64),
    ("secondary_end_x_mm", np.float64),
    ("secondary_end_y_mm", np.float64),
    ("secondary_end_z_mm", np.float64),
])

PHOTON_DTYPE = np.dtype([
    ("gun_call_id", np.int64),
    ("primary_track_id", np.int32),
    ("secondary_track_id", np.int32),
    ("photon_track_id", np.int32),
    ("_padding1", "V4"),  # 4-byte padding for alignment
    ("photon_creation_time_ns", np.float64),
    ("photon_origin_x_mm", np.float64),
    ("photon_origin_y_mm", np.float64),
    ("photon_origin_z_mm", np.float64),
    ("photon_scint_exit_x_mm", np.float64),
    ("photon_scint_exit_y_mm", np.float64),
    ("photon_scint_exit_z_mm", np.float64),
    ("optical_interface_hit_x_mm", np.float64),
    ("optical_interface_hit_y_mm", np.float64),
    ("optical_interface_hit_time_ns", np.float64),
    ("optical_interface_hit_dir_x", np.float64),
    ("optical_interface_hit_dir_y", np.float64),
    ("optical_interface_hit_dir_z", np.float64),
    ("optical_interface_hit_pol_x", np.float64),
    ("optical_interface_hit_pol_y", np.float64),
    ("optical_interface_hit_pol_z", np.float64),
    ("optical_interface_hit_energy_eV", np.float64),
    ("optical_interface_hit_wavelength_nm", np.float64),
])


def read_header(file_path: Path) -> Dict[str, Any]:
    """Read and parse binary file header."""
    with open(file_path, "rb") as f:
        header_bytes = f.read(HEADER_SIZE)
        if len(header_bytes) < HEADER_SIZE:
            raise ValueError(f"File too small: {file_path}")

        magic, version, record_size = struct.unpack(HEADER_FORMAT, header_bytes)

        if magic != b"SCINPIX\x00":
            raise ValueError(f"Invalid magic number in {file_path}: {magic}")

        if version != 1:
            raise ValueError(f"Unsupported version {version} in {file_path}")

        return {
            "magic": magic,
            "version": version,
            "record_size": record_size,
            "header_size": HEADER_SIZE,
        }


def read_binary_file(file_path: str | Path, dtype: np.dtype) -> pd.DataFrame:
    """Read binary file with given dtype and return as DataFrame."""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read and validate header
    header = read_header(file_path)

    # Verify record size matches
    expected_size = dtype.itemsize
    if header["record_size"] != expected_size:
        raise ValueError(
            f"Record size mismatch: file={header['record_size']}, "
            f"expected={expected_size} for {file_path.name}"
        )

    # Read all records after header
    with open(file_path, "rb") as f:
        f.seek(HEADER_SIZE)
        data = np.fromfile(f, dtype=dtype)

    # Convert to DataFrame, excluding padding fields
    df = pd.DataFrame(data)

    # Remove padding columns
    padding_cols = [col for col in df.columns if col.startswith("_padding")]
    df = df.drop(columns=padding_cols)

    # Decode species strings (remove null padding)
    for col in df.columns:
        if col.endswith("_species"):
            df[col] = df[col].str.decode("utf-8").str.rstrip("\x00")

    return df


def read_primaries(file_path: str | Path) -> pd.DataFrame:
    """Read primary particles from binary file."""
    return read_binary_file(file_path, PRIMARY_DTYPE)


def read_secondaries(file_path: str | Path) -> pd.DataFrame:
    """Read secondary particles from binary file."""
    return read_binary_file(file_path, SECONDARY_DTYPE)


def read_photons(file_path: str | Path) -> pd.DataFrame:
    """Read photons from binary file."""
    return read_binary_file(file_path, PHOTON_DTYPE)


def validate_output_directory(output_dir: str | Path) -> Dict[str, pd.DataFrame]:
    """
    Read all output files from a directory and return as dict of DataFrames.

    Returns:
        dict with keys "primaries", "secondaries", "photons"
    """
    output_dir = Path(output_dir)

    results = {}

    # Try to read each file type (.bin extension)
    primaries_file = output_dir / "primaries.bin"
    if primaries_file.exists():
        results["primaries"] = read_primaries(primaries_file)
        print(f"✅ Primaries: {len(results['primaries'])} rows")
    else:
        print(f"⚠️  Primaries file not found: {primaries_file}")

    secondaries_file = output_dir / "secondaries.bin"
    if secondaries_file.exists():
        results["secondaries"] = read_secondaries(secondaries_file)
        print(f"✅ Secondaries: {len(results['secondaries'])} rows")
    else:
        print(f"⚠️  Secondaries file not found: {secondaries_file}")

    photons_file = output_dir / "photons.bin"
    if photons_file.exists():
        results["photons"] = read_photons(photons_file)
        print(f"✅ Photons: {len(results['photons'])} rows")
    else:
        print(f"⚠️  Photons file not found: {photons_file}")

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python read_binary_output.py <output_directory>")
        sys.exit(1)

    output_dir = sys.argv[1]
    print(f"Reading binary output from: {output_dir}\n")

    try:
        results = validate_output_directory(output_dir)

        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)

        for name, df in results.items():
            print(f"\n{name.capitalize()}:")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

            if len(df) > 0:
                print(f"\nFirst few rows of {name}:")
                print(df.head())

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
