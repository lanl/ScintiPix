# ScintiPix Configuration Inputs

This document provides an overview of the main configuration inputs for ScintiPix. All simulation parameters are defined using Pydantic models, providing validation, type safety, and human-friendly YAML configuration files.

## Overview

ScintiPix uses a single, unified configuration object called `Simulation` (defined in `src/models/simulation.py`) that serves as the single source of truth for all parameters across the entire workflow. This configuration can be:

- Loaded from a YAML file (recommended for most users)
- Constructed programmatically in Python
- Mixed: load from YAML and override specific fields in code

The configuration is fully validated at load time, catching errors before the simulation runs.

## Top-Level Structure

The `Simulation` model contains seven main sections:

```yaml
source:           # Particle source definition (GPS commands)
scintillator:     # Scintillator geometry, material, and optical properties
geant4runner:     # Geant4 runtime controls and output settings
metadata:         # Run metadata, directory layout, and stage controls
optical:          # Lens system and optical transport (optional)
intensifier:      # Image intensifier configuration (optional)
sensor:           # Sensor/detector configuration (optional)
```

**Required sections**: `source`, `scintillator`, `geant4runner`, `metadata`

**Optional sections**: `optical`, `intensifier`, `sensor` (set to `null` or omit if not needed)

## Configuration Sections

### 1. Source (`source`)

Defines the particle source using Geant4 General Particle Source (GPS) commands and optional timing models.

**Key components**:
- `gps.particle`: Particle type (e.g., `neutron`, `gamma`, `proton`)
- `gps.position`: Spatial distribution (type, shape, center, radius)
- `gps.angular`: Angular distribution (beam direction, collimation)
- `gps.energy`: Energy distribution (mono-energetic or spectral)
- `timing`: Optional timing model (`none`, `continuous`, or `pulsed`)

**Example**:
```yaml
source:
  gps:
    particle: neutron
    position:
      type: Plane
      shape: Circle
      centerMm: {x_mm: 0.0, y_mm: 0.0, z_mm: -100.0}
      radiusMm: 10.0
    angular:
      type: beam2d
      direction: {x: 0.0, y: 0.0, z: 1.0}
    energy:
      type: Mono
      monoMeV: 6.0
  timing:
    mode: pulsed
    particle_flux: 3183.0
    pulse_period_ns: 1000000.0
    pulse_time_width_ns: 270.0
```

**Timing modes**:
- `none`: Standard Geant4 event-local timing
- `continuous`: Derives source times from particle flux and source area
- `pulsed`: Models pulsed sources with configurable period, width, and shape

See `src/models/source.py` for complete field definitions.

### 2. Scintillator (`scintillator`)

Defines the scintillator geometry, material composition, and optical properties.

**Key components**:
- `catalogId`: Reference to a pre-defined scintillator material (e.g., `EJ-276D`, `EJ-200`)
- `position_mm`: Center position of the scintillator (x, y, z)
- `dimension_mm`: Physical dimensions (x, y, z)
- `maskRadius`: Optional circular mask radius (for spatial filtering)
- `composition`: Optional custom material composition (overrides catalog)
- `optical`: Optional custom optical properties (overrides catalog)

**Example**:
```yaml
scintillator:
  catalogId: EJ-276D
  position_mm:
    x_mm: 0.0
    y_mm: 0.0
    z_mm: 0.0
  dimension_mm:
    x_mm: 100.0
    y_mm: 100.0
    z_mm: 20.0
  maskRadius: 18.0
```

**Catalog vs. custom**:
- Using `catalogId` loads pre-defined materials with validated optical properties
- Custom `composition` and `optical` sections allow full material specification
- Catalogs provide baseline properties that can be selectively overridden

See `src/models/scintillator.py` for complete field definitions and catalog structure.

### 3. Geant4 Runner (`geant4runner`)

Controls Geant4 runtime behavior, output settings, and performance options.

**Key components**:
- `numberOfParticles`: Number of primary particles to simulate
- `binary`: Path or command to the Geant4 executable
- `showProgress`: Enable/disable progress bar during simulation
- `verifyOutput`: Verify that expected output files are created
- `output`: Control which outputs are written (primaries, secondaries, photons)
- `photonCulling`: Optional photon culling based on acceptance angle
- `runtimeControls`: Geant4 verbosity levels

**Example**:
```yaml
geant4runner:
  numberOfParticles: 5000
  binary: scintipix
  showProgress: true
  verifyOutput: true
  output:
    primaries: true
    secondaries: true
    photons: true
  photonCulling:
    enabled: false
    acceptanceAngleDeg: 27.0
  runtimeControls:
    controlVerbose: 0
    runVerbose: 0
    eventVerbose: 0
    trackingVerbose: 0
    printProgress: 500
```

**Output control**:
- `primaries`: Write primary particle information to `primaries.bin`
- `secondaries`: Write secondary particle information to `secondaries.bin`
- `photons`: Write optical photon information to `simulatedPhotons.bin`

See `src/models/geant4runtime.py` for complete field definitions.

### 4. Metadata (`metadata`)

Defines run metadata, directory layout, and which simulation stages to execute.

**Key components**:
- `author`: Name of the person running the simulation
- `date`: Date of the simulation run
- `version`: ScintiPix version identifier
- `description`: Human-readable description of the simulation
- `RunControls`: Which stages to execute (focus, geant4, optics, intensifier, sensor)
- `RunEnvironment`: Directory layout and file naming

**Example**:
```yaml
metadata:
  author: Alex Long
  date: 2026-07-09
  version: ScintiPix v0.1
  description: Example simulation with EJ-276D scintillator
  RunControls:
    auto_focus_lens: false
    geant4_simulation: true
    transportation: false
    intensification: false
    sensor_detection: false
  RunEnvironment:
    WorkingDirectory: data
    SimulationRunID: example_run
    MacroDirectory: macros
    LogDirectory: logs
    SimulatedPhotonsDirectory: simulatedPhotons
    TransportedPhotonsDirectory: transportedPhotons
    PrimariesDirectory: primaries
    SecondariesDirectory: secondaries
```

**Run controls**:
- `auto_focus_lens`: Enable automatic lens focusing routine to determine optimal working distance (default: `false`)
  - When enabled, runs `src/optics/Calibration.py` to calculate the optimal `optical.interface.position_mm.z_mm` 
  - This should be run as a one-time setup step before the Geant4 simulation
  - The routine determines the working distance that achieves the desired magnification for the given lens prescription
  - See `.agents/docs/WORKFLOWS.md` for more details on the lens focusing subroutine
- Stages must be enabled sequentially (can't enable intensifier without optics)
- Typical workflow: start with `geant4_simulation: true` only, then add stages

**Directory layout**:
- All paths are relative to `WorkingDirectory`
- Directories are created automatically if they don't exist
- `SimulationRunID` is used as a prefix for output files

See `src/models/metadata.py` for complete field definitions.

### 5. Optical (`optical`) - Optional

Defines the lens system and optical transport configuration.

**Key components**:
- `lenses`: List of lens prescriptions (loaded from Zemax `.zmx` files)
- `interface`: Optical interface (scoring plane) configuration
  - `diameter_mm`: Circular aperture diameter (lens entrance or PMT diameter)
  - `position_mm`: Position of the optical interface relative to scintillator
- `showTransportProgress`: Enable/disable progress reporting

**Example**:
```yaml
optical:
  lenses:
    - catalogId: CanonEF50mmf1.0L
      primary: true
  interface:
    diameter_mm: 60.55          # Circular aperture diameter (lens or PMT)
    position_mm:
      x_mm: 0.0
      y_mm: 0.0
      z_mm: 210.05              # Working distance from scintillator
  showTransportProgress: true
```

**Design rationale**:
- Scintillators are always viewed through circular optics (lenses or PMTs), so the interface is always circular
- The `diameter_mm` specifies the acceptance aperture of your optical system
- The `position_mm.z_mm` is the working distance from the scintillator back face
- This simplified design eliminates unnecessary complexity from sensor-level constraints

**Automatic lens focusing**:
- You can manually specify `position_mm.z_mm` or use the automatic focusing routine
- Enable `metadata.RunControls.auto_focus_lens: true` to automatically calculate the optimal working distance
- The automatic routine uses the lens prescription and desired magnification to determine `position_mm.z_mm`
- This is a one-time setup step that should be run before the Geant4 simulation
- Manual specification is faster if you already know the correct working distance

**Note**: The optics stage is under active development. See `.agents/docs/OPTICS.md` for current status.

See `src/models/optics.py` for complete field definitions.

### 6. Intensifier (`intensifier`) - Optional

Defines the image intensifier configuration.

**Key components**:
- `model`: Intensifier model identifier (e.g., `Cricket2`)
- `input_screen`: Input screen geometry and magnification
- `output_screen`: Output screen properties (if applicable)

**Example**:
```yaml
intensifier:
  model: Cricket2
  input_screen:
    image_circle_diameter_mm: 18.0
    center_mm: [0.0, 0.0]
    magnification: 1.0
    coordinate_frame: intensifier_input_plane
```

**Note**: The intensifier stage is under active development.

See `src/models/intensifier.py` for complete field definitions.

### 7. Sensor (`sensor`) - Optional

Defines the sensor/detector configuration.

**Key components**:
- `model`: Sensor model identifier (e.g., `Timepix3`)
- `timepix`: Timepix-specific parameters (if applicable)

**Example**:
```yaml
sensor:
  model: Timepix3
  timepix:
    pixels_x: 256
    pixels_y: 256
    pixel_pitch_mm: 0.055
    max_tot_ns: 25550.0
    dead_time_ns: 475.0
```

**Note**: The sensor stage is under active development.

See `src/models/sensor.py` for complete field definitions.

## Loading and Using Configurations

### From YAML

```python
from pathlib import Path
from src.models.simulation import Simulation

# Load configuration from YAML
config = Simulation.model_validate_yaml(Path("config.yaml").read_text())

# Access fields
print(config.source.gps.particle)
print(config.scintillator.catalogId)
print(config.geant4runner.numberOfParticles)
```

### Programmatic Construction

```python
from src.models.simulation import Simulation
from src.models.source import Source, SourceGps
from src.models.scintillator import Scintillator

config = Simulation(
    source=Source(gps=SourceGps(particle="neutron", ...)),
    scintillator=Scintillator(catalogId="EJ-276D", ...),
    ...
)
```

### Hybrid Approach

```python
# Load base config from YAML
config = Simulation.model_validate_yaml(Path("base_config.yaml").read_text())

# Override specific fields
config.geant4runner.numberOfParticles = 10000
config.metadata.description = "Modified run with 10k particles"
```

## Example Configurations

Complete example configurations are provided in `examples/yamlFiles/`:

- `EJ276D.yaml`: Full example with EJ-276D scintillator, intensifier, and sensor
- `EJ200.yaml`: Example with EJ-200 scintillator
- `CanonEF50mmf1p0L_example.yaml`: Example with Canon lens configuration
- `pulsed_neutron_source_timing.yaml`: Pulsed neutron source example
- `continuous_neutron_source_timing.yaml`: Continuous neutron source example

## Validation

All configurations are validated at load time using Pydantic. Common validation errors include:

- Missing required fields
- Invalid field types
- Values out of allowed ranges
- Inconsistent combinations (e.g., enabling intensifier without optics)

Validation errors provide detailed messages indicating which field failed and why.

## Units

ScintiPix uses explicit units in field names to avoid ambiguity:

- Distance: `_mm` (millimeters)
- Time: `_ns` (nanoseconds)
- Energy: `_MeV` (mega-electronvolts) or `_eV` (electronvolts)
- Angle: `_deg` (degrees) or `Deg` suffix

Some fields accept `ValueWithUnit` objects for flexibility:
```yaml
scintYield: "10000 photons/MeV"
timeConstant: "270 ns"
density: "1.096 g/cm³"
```

## Further Reading

- **Workflow**: See `.agents/docs/WORKFLOWS.md` for how configuration flows through the simulation pipeline
- **Outputs**: See `.agents/docs/OUTPUT.md` for details on binary output formats
- **Optics**: See `.agents/docs/OPTICS.md` for optical transport configuration details
- **Models**: See `src/models/*.py` for complete Pydantic model definitions with field documentation
