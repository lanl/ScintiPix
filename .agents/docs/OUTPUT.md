# ScintiPix Simulation Output Format

## Overview

ScintiPix uses a simple, thread-safe binary format for simulation output. This provides:
- **Fast writes**: Direct `fwrite()` of fixed-size structs with persistent file handles
- **Thread-safe**: Run-start file initialization plus per-output locking around appends from GEANT4 worker threads
- **Simple**: No external dependencies, standard C file I/O
- **Compact**: Fixed-size records with minimal overhead

The output of a ScintiPix simulation run is organized into a directory structure under the run root:

```text
run_id/
  logs/
    runLog.txt
  macros/
    run_000.mac
  primaries/
    primaries.bin
  secondaries/
    secondaries.bin
  simulatedPhotons/
    photons.bin
  transportedPhotons/
    photons.bin
```

## Output Stages

ScintiPix currently defines these binary output datasets:

- **`primaries/`**: Primary particles generated in the simulation
- **`secondaries/`**: Secondary particles produced from interactions of primaries
- **`simulatedPhotons/`**: Optical photons generated and detected at the optical interface
- **`transportedPhotons/`**: Optical photons transported to the intensifier photocathode

All output stages use the same binary file format (described below).

The Python optics stage uses the same 64-byte header for transported photons.

---

## Binary File Format

### File Structure

Each `.bin` file consists of:
1. **64-byte header** (file metadata)
2. **Contiguous array of fixed-size records** (actual data)

### Header (64 bytes)

```c
struct BinaryHeader {
  char magic[8];            // "SCINPIX\0"
  uint32_t version;         // Format version (currently 1)
  uint32_t recordSize;      // Size of each record in bytes
  uint64_t recordCount;     // Number of records (informational)
  char padding[40];         // Reserved for future use
};
```

### Record Sizes

- **Primary particles**: 96 bytes per record
- **Secondary particles**: 96 bytes per record
- **Photons**: 168 bytes per record
- **Transported photons**: 72 bytes per record

Each struct uses C-style alignment (natural padding after `int32` fields to maintain 8-byte alignment for `double`/`int64`).

### Thread Safety

The format is thread-safe because:

1. **Run-start headers**: Selected output files are created/truncated and given headers before worker appends begin
2. **Thread-local file handles**: Each GEANT4 worker thread maintains its own append handle
3. **Append mode**: Worker handles use binary append mode, so writes go to the end of file
4. **Per-output locking**: Appends are serialized per output file inside `SimIO`
5. **Fixed-size records**: No variable-length data or offsets are shared between writers

Multiple GEANT4 worker threads can write the same selected output safely through `SimIO::AppendOutput`.

---

## Dataset Schemas

### primaries (96 bytes per record)

The `primaries/` dataset contains information about the primary particles generated in the simulation.

| Field                                          | Type      | Offset | Size | Description |
|------------------------------------------------|-----------|--------|------|-------------|
| gun_call_id                                    | int64     | 0      | 8    | Identifier for the GEANT4 event |
| primary_track_id                               | int32     | 8      | 4    | Primary particle track ID in GEANT4 |
| _padding_                                      | -         | 12     | 4    | Alignment padding |
| primary_species                                | char[24]  | 16     | 24   | Particle species (e.g., "neutron", "gamma", "proton") |
| primary_x_mm                                   | double    | 40     | 8    | X-coordinate of primary position (mm) |
| primary_y_mm                                   | double    | 48     | 8    | Y-coordinate of primary position (mm) |
| primary_energy_MeV                             | double    | 56     | 8    | Energy of primary particle (MeV) |
| primary_interaction_time_ns                    | double    | 64     | 8    | Time of first interaction in scintillator (ns) |
| primary_created_secondary_count                | int64     | 72     | 8    | Number of secondaries created |
| primary_generated_optical_photon_count         | int64     | 80     | 8    | Number of optical photons generated |
| primary_detected_optical_interface_photon_count| int64     | 88     | 8    | Number of photons detected at optical interface |

**Notes:**
- Source creation and pulse timing values are used internally to set the GEANT4 primary vertex time
- They are not recorded in `primaries.bin`; the only primary timing field persisted is `primary_interaction_time_ns`
- Only primaries that created at least one secondary in the scintillator are recorded

### secondaries (96 bytes per record)

The `secondaries/` dataset contains information about secondary particles produced from interactions of primaries.

| Field                        | Type      | Offset | Size | Description |
|------------------------------|-----------|--------|------|-------------|
| gun_call_id                  | int64     | 0      | 8    | GEANT4 event identifier (links to primary) |
| primary_track_id             | int32     | 8      | 4    | Primary particle track ID |
| secondary_track_id           | int32     | 12     | 4    | Secondary particle track ID |
| secondary_species            | char[24]  | 16     | 24   | Particle species (e.g., "neutron", "electron") |
| secondary_origin_x_mm        | double    | 40     | 8    | X-coordinate of secondary origin (mm) |
| secondary_origin_y_mm        | double    | 48     | 8    | Y-coordinate of secondary origin (mm) |
| secondary_origin_z_mm        | double    | 56     | 8    | Z-coordinate of secondary origin (mm) |
| secondary_origin_energy_MeV  | double    | 64     | 8    | Energy at origin (MeV) |
| secondary_end_x_mm           | double    | 72     | 8    | X-coordinate of end position (mm) |
| secondary_end_y_mm           | double    | 80     | 8    | Y-coordinate of end position (mm) |
| secondary_end_z_mm           | double    | 88     | 8    | Z-coordinate of end position (mm) |

**Notes:**
- No timing information is recorded for secondaries
- Timing must be inferred from the relationship between primaries and photons
- If no usable end position was recorded, the `secondary_end_*_mm` fields will be `NaN`
- Only secondaries that generated at least one detected optical photon are recorded

### simulatedPhotons (168 bytes per record)

The `simulatedPhotons/` dataset contains information about optical photons generated in the scintillator and detected at the optical interface.

| Field                                  | Type      | Offset | Size | Description |
|----------------------------------------|-----------|--------|------|-------------|
| gun_call_id                            | int64     | 0      | 8    | GEANT4 event identifier |
| primary_track_id                       | int32     | 8      | 4    | Primary particle track ID (links to primary) |
| secondary_track_id                     | int32     | 12     | 4    | Secondary particle track ID (links to secondary) |
| photon_track_id                        | int32     | 16     | 4    | Photon track ID in GEANT4 |
| _padding_                              | -         | 20     | 4    | Alignment padding |
| photon_creation_time_ns                | double    | 24     | 8    | Time photon created in scintillator (ns) |
| photon_origin_x_mm                     | double    | 32     | 8    | X-coordinate of photon origin (mm) |
| photon_origin_y_mm                     | double    | 40     | 8    | Y-coordinate of photon origin (mm) |
| photon_origin_z_mm                     | double    | 48     | 8    | Z-coordinate of photon origin (mm) |
| photon_scint_exit_x_mm                 | double    | 56     | 8    | X-coordinate of scintillator exit (mm) |
| photon_scint_exit_y_mm                 | double    | 64     | 8    | Y-coordinate of scintillator exit (mm) |
| photon_scint_exit_z_mm                 | double    | 72     | 8    | Z-coordinate of scintillator exit (mm) |
| optical_interface_hit_x_mm             | double    | 80     | 8    | X-coordinate at optical interface (mm) |
| optical_interface_hit_y_mm             | double    | 88     | 8    | Y-coordinate at optical interface (mm) |
| optical_interface_hit_time_ns          | double    | 96     | 8    | Time at optical interface (ns) |
| optical_interface_hit_dir_x            | double    | 104    | 8    | X-component of photon direction |
| optical_interface_hit_dir_y            | double    | 112    | 8    | Y-component of photon direction |
| optical_interface_hit_dir_z            | double    | 120    | 8    | Z-component of photon direction |
| optical_interface_hit_pol_x            | double    | 128    | 8    | X-component of photon polarization |
| optical_interface_hit_pol_y            | double    | 136    | 8    | Y-component of photon polarization |
| optical_interface_hit_pol_z            | double    | 144    | 8    | Z-component of photon polarization |
| optical_interface_hit_energy_eV        | double    | 152    | 8    | Photon energy at interface (eV) |
| optical_interface_hit_wavelength_nm    | double    | 160    | 8    | Photon wavelength at interface (nm) |

**Notes:**
- If no exit position was recorded, the `photon_scint_exit_*_mm` fields will be `NaN`
- If no hit position was recorded at the optical interface, the `optical_interface_hit_*` fields will be `NaN`
- The `optical_interface_hit_*` fields capture position, time, direction, polarization, energy, and wavelength at the optical-interface crossing
- Timing information in `photon_creation_time_ns` and `optical_interface_hit_time_ns` share the same GEANT4 event-local global-time basis, allowing for time-of-flight analysis

### transportedPhotons (72 bytes per record)

The `transportedPhotons/` dataset contains only photons that RayOptics traced
successfully to the active photocathode area.

| Field                               | Type   | Offset | Size |
|-------------------------------------|--------|--------|------|
| source_photon_index                 | int64  | 0      | 8    |
| gun_call_id                         | int64  | 8      | 8    |
| primary_track_id                    | int32  | 16     | 4    |
| secondary_track_id                  | int32  | 20     | 4    |
| photon_track_id                     | int32  | 24     | 4    |
| _padding_                           | -      | 28     | 4    |
| photocathode_hit_x_mm               | double | 32     | 8    |
| photocathode_hit_y_mm               | double | 40     | 8    |
| photocathode_hit_z_mm               | double | 48     | 8    |
| photocathode_hit_time_ns            | double | 56     | 8    |
| photocathode_hit_wavelength_nm      | double | 64     | 8    |

Blocked, missed, invalid, and out-of-bounds rays are omitted rather than stored
as transported photons.

---

## Reading Binary Output in Python

Use the provided Python reader to load binary files into pandas DataFrames:

```python
import sys
sys.path.append('scripts')
import read_binary_output as reader

# Read individual files
primaries_df = reader.read_primaries("output/primaries.bin")
secondaries_df = reader.read_secondaries("output/secondaries.bin")
photons_df = reader.read_photons("output/photons.bin")

# Or read entire directory
results = reader.validate_output_directory("output/")
```

The DataFrames have column names matching the field names in the tables above, with the same units.

---

## Converting to Other Formats

The Python reader loads data into pandas DataFrames, which can be easily exported:

```python
import read_binary_output as reader

df = reader.read_photons("output/photons.bin")

# Convert to Parquet for long-term storage
df.to_parquet("photons.parquet", compression="snappy")

# Convert to HDF5 for compatibility
df.to_hdf("photons.h5", key="photons", mode="w")

# Convert to CSV for inspection
df.to_csv("photons.csv", index=False)
```

---

## Performance Characteristics

**Write performance:**
- 5000 events with ~5.4 MB photon output: **~10 seconds** (including full GEANT4 simulation)
- Binary I/O overhead is negligible compared to physics tracking
- Throughput: **~500 events/second** for typical scintillator simulations

**File sizes** (typical 5000-event simulation):
- Primaries: ~36 KB
- Secondaries: ~109 KB
- Photons: ~5.4 MB

**Memory usage:**
- Simulation runtime: ~50 MB (buffered output + physics)
- No end-of-run memory spike (unlike HDF5/Parquet batch writes)

---

## Implementation Details

Record structures are defined in `sim/include/structures.hh`:

```cpp
namespace SimStructures {
namespace detail {

struct BinaryPrimaryRow {
  std::int64_t gun_call_id;
  std::int32_t primary_track_id;
  // padding inserted by compiler for alignment
  char primary_species[24];
  double primary_x_mm;
  double primary_y_mm;
  double primary_energy_MeV;
  double primary_interaction_time_ns;
  std::int64_t primary_created_secondary_count;
  std::int64_t primary_generated_optical_photon_count;
  std::int64_t primary_detected_optical_interface_photon_count;
};

// Similar structures for BinarySecondaryRow and BinaryPhotonRow
}  // namespace detail
}  // namespace SimStructures
```

Binary I/O implementation is in `sim/src/SimIO.cc`:
- `InitOutput()`: Validates output paths exist
- `AppendOutput()`: Converts semantic structs to binary rows and appends to files
- `CloseOutput()`: Closes persistent file handles at run end

---

## Migration from HDF5/Parquet

If you have existing analysis code that used HDF5:

**Before (HDF5)**:
```python
import pandas as pd
df = pd.read_hdf("primaries.h5", key="/primaries")
```

**After (Binary)**:
```python
import read_binary_output as reader
df = reader.read_primaries("primaries.bin")
```

The DataFrames have identical schemas - only the file format changed. All downstream analysis code should work without modification.
