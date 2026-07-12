# Example YAML Files

This folder contains shared `Simulation` YAML inputs used by the scripts under
`examples/`. The authoritative schema is defined under `src/models/`, with the
top-level model in `src/models/simulation.py`. YAML loading is implemented by
`src.config.yaml.from_yaml(...)`.

Current files:
- `CanonEF50mmf1p0L_example.yaml`: primary end-to-end example configuration
- `continuous_neutron_source_timing.yaml`: lightweight continuous source timing
  example for Geant4 `/primaries` timing. Uses `particle_flux` to derive fixed
  event spacing.
- `EJ200.yaml`: catalog-driven scintillator example with overrides
- `EJ276D.yaml`: catalog-driven EJ-276D timing-component example
- `pulsed_neutron_source_timing.yaml`: lightweight pulsed source timing example
  for Geant4 `/primaries` timing. Uses `particle_flux`, `pulse_period_ns`,
  `pulse_time_offset_ns`, and `pulse_time_width_ns`.
- `three_component_timing_example.yaml`: explicit scintillation timing example

All example YAMLs include:
- a `source.timing` block for source-time macro generation
- an `intensifier` block for post-transport staged intensifier response
- a `sensor.timepix` block for downstream centered single-chip Timepix3 readout

`source.timing` is emitted by the Python configuration layer as
`/source/timing/*` macro commands and consumed by the Geant4 runtime when
generating primary vertices.

The source-neutron timing examples are consumed by
[`examples/sourceTiming/README.md`](../sourceTiming/README.md). They are
Geant4-only inspection inputs; downstream optical, intensifier, and sensor
blocks are present for schema and geometry completeness.

## Schema Rules

`Simulation` rejects unknown keys. Use the field names below or the listed
aliases where provided.

Relative paths in run-environment settings are resolved by the configuration
helpers before macro writing and pipeline execution.

## Top-Level Blocks

Required:
- `scintillator`: scintillator geometry and material/optical properties
- `source`: Geant4 GPS source settings and optional source timing
- `metadata`: run metadata, stage controls, and output directory layout
- `geant4runner`: Geant4 run controls, output selection, and particle count

Optional:
- `optical`: lens and optical-interface geometry assumptions
- `intensifier`: image-intensifier model and response parameters
- `sensor`: Timepix sensor/readout parameters

## `scintillator`

Defines scintillator size, position, mask, and material properties.

Fields:
- `catalogId`: optional scintillator catalog identifier. When present,
  `src.config.yaml.from_yaml(...)` hydrates missing `properties` fields from the
  bundled scintillator catalog.
- `position_mm`: required scintillator center position.
  - `x_mm`
  - `y_mm`
  - `z_mm`
- `dimension_mm`: required scintillator dimensions. Each component must be
  greater than zero.
  - `x_mm`
  - `y_mm`
  - `z_mm`
- `maskRadius`: optional circular mask pass-through radius in mm. Defaults to
  `0.0`, which disables the mask. Accepted aliases include `maskRadiusMm` and
  `mask_radius_mm`.
- `properties`: optional only when `catalogId` is provided; otherwise required.

### `scintillator.properties`

Defines the optical/material table emitted into Geant4 macros.

Required when not provided by a catalog:
- `name`: material name used by the Geant4 scintillator material command
- `composition`: material density and atom counts
- `optical`: optical tables and scintillation response

### `scintillator.properties.composition`

- `density`: density in g/cm3; must be greater than zero
- `atoms`: mapping of element symbols to positive atom counts

### `scintillator.properties.optical`

Required for inline optical tables:

- `photonEnergy`: photon-energy table in eV; length must match `nKEntries`
- `rIndex`: refractive-index table; length must match `nKEntries`
- `nKEntries`: number of optical table entries; must be greater than zero

Optional optical fields:

- `absLength`: absorption-length table in cm; if present, length must match
  `nKEntries`
- `scintSpectrum`: emission-spectrum table; if present, length must match
  `nKEntries`
- `timeComponents`: scintillation decay profiles
- `scintYield`: scintillation yield in photons/MeV; must be greater than zero
- `resolutionScale`: Geant4 scintillation resolution scale; must be greater
  than zero

### `scintillator.properties.optical.timeComponents`

Particle-keyed scintillation timing profiles. At least one profile is required.
Supported profile keys:
- `default`
- `neutron`
- `gamma`

Each profile must contain exactly three components. Every component has:
- `timeConstant`: decay time in ns; must be non-negative
- `yieldFraction`: component yield fraction; must be non-negative

The three `yieldFraction` values in a profile must sum to approximately `1.0`.
At least one component must have both `timeConstant > 0` and
`yieldFraction > 0`.

Profile selection follows the configured source particle:
- neutron sources prefer `neutron`, then `default`
- gamma sources prefer `gamma`, then `default`
- if only one particle-specific profile exists, it can be used as the fallback

## `source`

Defines the primary particle source. The `gps` block maps to Geant4
`G4GeneralParticleSource`; the optional `timing` block maps to ScintiPix source
timing commands.

### `source.gps`

Fields:
- `particle`: required particle name, for example `neutron`
- `position`: required GPS position distribution
- `angular`: optional GPS angular distribution; defaults to a beam along `+z`
- `energy`: required GPS energy distribution

### `source.gps.position`

Fields:
- `type`: GPS position distribution type. Defaults to `Plane`.
- `shape`: GPS position shape. Defaults to `Circle`.
- `centerMm`: required source center position in mm.
  - `x_mm`
  - `y_mm`
  - `z_mm`
- `radiusMm`: required source radius in mm; must be greater than zero

### `source.gps.angular`

Fields:
- `type`: GPS angular distribution type. Defaults to `beam2d`.
- `rot1`: first angular rotation vector. Defaults to `{x: 1.0, y: 0.0, z: 0.0}`.
- `rot2`: second angular rotation vector. Defaults to `{x: 0.0, y: 1.0, z: 0.0}`.
- `direction`: beam direction vector. Defaults to `{x: 0.0, y: 0.0, z: 1.0}`.

Each vector uses:
- `x`
- `y`
- `z`

### `source.gps.energy`

Fields:
- `type`: GPS energy distribution type. Defaults to `Mono`.
- `monoMeV`: required when `type` is `Mono`; monoenergetic kinetic energy in
  MeV and must be greater than zero.

### `source.timing`

Optional source-time model in global nanoseconds. When omitted, generated
macros keep the current event-local Geant4 timing behavior. When present, the
Python configuration layer emits `/source/timing/*` macro commands, and the
Geant4 primary generator assigns the resulting source time to each generated
primary vertex.

Common fields:
- `mode`: one of `none`, `continuous`, or `pulsed`. Defaults to `none`.
- `start_time_ns`: global time of the first source event or pulse. Defaults to
  `0.0`. Accepted aliases include `startTimeNs` and `startTime`.

Continuous mode:

```yaml
source:
  timing:
    mode: continuous
    start_time_ns: 0.0
    particle_flux: 3183098.861837907
```

Fields:
- `particle_flux`: required for `continuous`; particle flux in particles per
  second per square centimeter. The Python configuration layer combines this
  with the circular GPS source radius to derive the Geant4 event spacing.
  Accepted alias: `particleFlux`.

Pulsed mode:

```yaml
source:
  timing:
    mode: pulsed
    start_time_ns: 0.0
    particle_flux: 3183.098861837907
    pulse_period_ns: 1000000.0
    pulse_time_offset_ns: 0.0
    pulse_time_width_ns: 270.0
    pulse_shape: uniform
```

Fields:
- `particle_flux`: required for `pulsed`; particle flux in particles per second
  per square centimeter. The Python configuration layer combines this with the
  circular GPS source radius and `pulse_period_ns` to derive Geant4 events per
  pulse. Accepted alias: `particleFlux`.
- `pulse_period_ns`: required for `pulsed`; time between pulse starts. Must be
  greater than zero. Accepted aliases include `pulsePeriodNs` and `pulsePeriod`.
- `pulse_time_offset_ns`: optional for `pulsed`; offset from T-zero to pulse
  start. Defaults to `0.0`. Accepted aliases include `pulseTimeOffsetNs` and
  `pulseTimeOffset`.
- `pulse_time_width_ns`: required for `pulsed`; neutron creation times are
  randomly distributed over this window during Geant4 primary generation. Must
  be non-negative. Accepted aliases include `pulseTimeWidthNs` and
  `pulseTimeWidth`.
- `pulse_shape`: currently only `uniform` is accepted. Accepted alias:
  `pulseShape`.

Pulsed event grouping uses:

```text
particles_per_pulse = ceil(particle_flux * source_area_cm2 * pulse_period_ns / 1e9)
pulse_id = event_id // particles_per_pulse
pulse_start_time = start_time + pulse_id * pulse_period
creation_time = pulse_start_time + pulse_time_offset + random_uniform(0, pulse_time_width)
```

Geant4 transport determines the relativistic neutron time of flight from the
configured source position to the scintillator interaction.

The simulation uses the assigned source creation time internally as the Geant4
primary vertex time. `/primaries` records only `primary_interaction_time_ns` for
primary timing; source creation and pulse metadata are not persisted there.

## `optical`

Defines the primary optical lens and the Geant4 optical-interface plane used as
input to downstream optical transport.

Fields:
- `lenses`: required list of lens descriptors. Exactly one lens must have
  `primary: true`.
- `interface`: required optical-interface aperture, position, and optional
  working-distance bounds.
- `showTransportProgress`: optional transport progress display flag. Defaults
  to `true`. Alias: `show_transport_progress`.
- `transportAssumptions`: optional physical assumptions used by downstream
  transport. Defaults are shown below.

### `optical.lenses[]`

Each lens entry must provide `catalogId` and/or `zmxFile`.

Fields:
- `name`: optional display name. If omitted, it is filled from `catalogId` or
  the `zmxFile` stem.
- `primary`: required boolean. Exactly one lens in the list must be primary.
- `catalogId`: optional lens catalog identifier. Catalog-backed configs are
  hydrated by `src.config.yaml.from_yaml(...)`.
- `zmxFile`: optional Zemax lens file path or catalog-resolved filename.
- `smxFile`: optional rayoptics sidecar file path or catalog-resolved filename.
- `focusGaps`: internal prescription gaps moved by autofocus.
- `focusAdjustmentMm`: current internal focus adjustment.
- `focusAdjustmentBoundsMm`: optional permitted internal focus travel.
- `backFocusMm`: last modeled optical surface to photocathode distance.
- `backFocusBoundsMm`: optional permitted back-focus interval.

### `optical.interface`

Fields:
- `diameterMm`: lens-entrance/scoring-plane diameter; must be greater than zero.
- `positionMm`: absolute optical-interface center position in mm.
  - `x_mm`
  - `y_mm`
  - `z_mm`
- `workingDistanceBoundsMm`: required autofocus search interval measured from
  the scintillator back face to the lens entrance.

Autofocus bounds in tests and examples are illustrative unless the associated
lens, mount, adapter, and intensifier assembly has been mechanically validated.

### `optical.transportAssumptions`

Fields:
- `objectPlane`: currently `scintillator_back_face`.
- `opticalInterfaceRepresents`: currently `lens_entrance_plane`.

## `intensifier`

Optional image-intensifier model used by the staged sensor pipeline.

Fields:
- `model`: required intensifier model label.
- `write_output_hdf5`: optional boolean controlling standalone intensifier HDF5
  writing. Defaults to `false`. Alias: `writeOutputHdf5`.
- `input_screen`: required active input-screen definition. Alias:
  `inputScreen`.
- `photocathode`: optional photocathode response parameters.
- `mcp`: optional MCP gain/spread parameters.
- `phosphor`: optional phosphor output parameters.

### `intensifier.input_screen`

Fields:
- `image_circle_diameter_mm`: active image-circle diameter in mm; must be
  greater than zero. Alias: `imageCircleDiameterMm`.
- `center_mm`: input-screen center as `[x_mm, y_mm]`. Defaults to `[0.0, 0.0]`.
  Also accepts `centerMm` and mapping forms with `x_mm`/`y_mm` or `x`/`y`.
- `magnification`: input-screen magnification. Defaults to `1.0` and must be
  greater than zero.
- `coordinate_frame`: coordinate-frame label. Defaults to
  `intensifier_input_plane`. Alias: `coordinateFrame`.
- `notes`: optional free-text note.

### `intensifier.photocathode`

Fields:
- `qe_wavelength_nm`: QE wavelength nodes in nm. Defaults to
  `[350.0, 500.0, 650.0]`. Alias: `qeWavelengthNm`.
- `qe_values`: QE values corresponding to `qe_wavelength_nm`. Defaults to
  `[0.15, 0.25, 0.05]`. Alias: `qeValues`.
- `collection_efficiency`: electron collection efficiency in `[0, 1]`.
  Defaults to `1.0`. Alias: `collectionEfficiency`.
- `tts_sigma_ns`: transit-time-spread sigma in ns. Defaults to `0.0` and must
  be non-negative. Alias: `ttsSigmaNs`.

The QE wavelength and value lists must have the same length. Wavelength nodes
must be monotonic increasing, and QE values must lie in `[0, 1]`.

### `intensifier.mcp`

Fields:
- `stage1_mean_gain`: default `8.0`; alias `stage1MeanGain`
- `stage1_gain_shape`: default `2.0`; alias `stage1GainShape`
- `stage2_mean_gain`: default `800.0`; alias `stage2MeanGain`
- `stage2_gain_shape`: default `2.0`; alias `stage2GainShape`
- `gain_ref`: default `1000.0`; alias `gainRef`
- `spread_sigma0_mm`: default `0.03`; alias `spreadSigma0Mm`
- `spread_gain_exponent`: default `0.4`; alias `spreadGainExponent`

Gain and gain-shape fields must be greater than zero. `spread_sigma0_mm` must
be non-negative.

### `intensifier.phosphor`

Fields:
- `phosphor_gain`: default `1.0`; must be greater than zero. Alias:
  `phosphorGain`.
- `decay_fast_ns`: default `70.0`; must be non-negative. Alias:
  `decayFastNs`.
- `decay_slow_ns`: default `200.0`; must be non-negative. Alias:
  `decaySlowNs`.
- `fast_fraction`: default `0.9`; must lie in `[0, 1]`. Alias:
  `fastFraction`.
- `psf_sigma_mm`: default `0.04`; must be non-negative. Alias:
  `psfSigmaMm`.

## `sensor`

Optional downstream sensor/readout configuration.

Fields:
- `model`: required sensor model label. Must not be blank.
- `timepix`: required Timepix geometry and simplified readout settings.

### `sensor.timepix`

Fields:
- `pixels_x`: number of sensor pixels in X. Defaults to `256` and must be
  greater than zero. Alias: `pixelsX`.
- `pixels_y`: number of sensor pixels in Y. Defaults to `256` and must be
  greater than zero. Alias: `pixelsY`.
- `pixel_pitch_mm`: pixel pitch in mm. Defaults to `0.055` and must be greater
  than zero. Alias: `pixelPitchMm`.
- `max_tot_ns`: maximum Time-over-Threshold value in ns. Defaults to `25550.0`
  and must be greater than zero. Alias: `maxTotNs`.
- `dead_time_ns`: per-pixel dead time in ns. Defaults to `475.0` and must be
  non-negative. Alias: `deadTimeNs`.

## `geant4runner`

Geant4 run-control and Python launch settings. If present, it must include
`numberOfParticles` and/or `runtimeControls`.

Fields:
- `numberOfParticles`: optional `/run/beamOn` particle count. Must be greater
  than zero.
- `runtimeControls`: optional macro preamble controls.
- `binary`: scintipix executable command. Defaults to `scintipix` and must not
  be blank.
- `eventsPerOutput`: Geant4 events buffered by each worker before writing one
  Parquet part file. Defaults to `1000`.
- `output`: selects which Geant4 Parquet tables are assembled and written.
  Defaults to all tables enabled. At least one of `primaries`, `secondaries`,
  or `photons` must be `true`.
- `photonCulling`: optional photon culling optimization settings.
- `resolutionTarget`: optional Geant4-side Siemens star resolution target.
- `showProgress`: Python runner progress display flag. Defaults to `false`.
- `verifyOutput`: check for expected simulation Parquet part files after
  simulation. Defaults to `true`.

### `geant4runner.runtimeControls`

If present, at least one field must be set.

Fields:
- `controlVerbose`: `/control/verbose`; must be non-negative.
- `runVerbose`: `/run/verbose`; must be non-negative.
- `eventVerbose`: `/event/verbose`; must be non-negative.
- `trackingVerbose`: `/tracking/verbose`; must be non-negative.
- `printProgress`: `/run/printProgress`; must be greater than zero.
- `storeTrajectory`: `/tracking/storeTrajectory`; boolean.

### `geant4runner.resolutionTarget`

Optional Siemens star absorber target placed on the scintillator `+Z` face.
Defaults to disabled. When enabled, the clear and opaque sectors are controlled
by the line-pair count; the inner radius and thickness are fixed in the Geant4
geometry.

Fields:
- `resolutionTargetEnabled`: boolean. Defaults to `false`.
- `resolutionTargetOuterRadiusMm`: outer radius in mm. Defaults to `100.0` and
  must be greater than zero.
- `resolutionTargetLinePairs`: number of opaque/clear line pairs. Defaults to
  `64` and must be greater than zero.

Example:

```yaml
geant4runner:
  numberOfParticles: 5000
  resolutionTarget:
    resolutionTargetEnabled: true
    resolutionTargetOuterRadiusMm: 50.0
    resolutionTargetLinePairs: 64
```

## `Metadata`

Run metadata and output layout. The top-level key may be `Metadata` or
`metadata`; examples use `Metadata`.

Fields:
- `author`: required non-empty author string.
- `date`: required string. YAML date scalars are normalized to ISO date strings.
- `version`: required non-empty version string.
- `description`: required non-empty description string.
- `RunEnvironment`: run directory and filename context.

### `Metadata.RunEnvironment`

Fields:
- `SimulationRunID`: run ID used for the run-root directory. Defaults to
  `example`.
- `SubRunNumber`: zero-padded sub-run number encoded in output filenames.
  Defaults to `0`; valid range is `0` to `9999`.
- `WorkingDirectory`: root data directory. Defaults to `data`.
- `MacroDirectory`: macro output directory under the run root. Defaults to
  `macros`.
- `LogDirectory`: log output directory under the run root. Defaults to `logs`.
- `OutputInfo`: stage output directory names and transport chunking controls.

Resolved layout:

```text
<WorkingDirectory>/<SimulationRunID>/
  <MacroDirectory>/
  <LogDirectory>/
  <OutputInfo.SimulatedPhotonsDirectory>/
  <OutputInfo.TransportedPhotonsDirectory>/
```

### `Metadata.RunEnvironment.OutputInfo`

Fields:
- `SimulatedPhotonsDirectory`: simulation-stage HDF5 directory. Defaults to
  `simulatedPhotons`. Accepted aliases include `simulated_photons_dir` and
  `simulatedPhotonsDir`.
- `TransportedPhotonsDirectory`: optical-transport HDF5 directory. Defaults to
  `transportedPhotons`. Accepted aliases include `transported_photons_dir` and
  `transportedPhotonsDir`.
- `TransportChunkRows`: optical-transport chunk row control. Defaults to
  `auto`; may be `auto` or a positive integer.
- `TransportChunkTargetMiB`: target memory budget in MiB for automatic
  optical-transport chunk sizing. Defaults to `32.0` and must be greater than
  zero.

## Going from YAML to Macro Generation

The YAML configuration is processed into a sequence of Geant4 macro commands
that initialize the simulation environment, geometry, source, and beam setup.
`src.config.macro.write_macro(...)` writes commands assembled in this order:

1. `geant4runner.runtimeControls`: runtime parameters and verbosity settings
2. `/output/*` commands from `Metadata.RunEnvironment`: output directory setup
3. scintillator and optical-interface geometry/material commands: physics models
4. `/run/initialize`: initialize the Geant4 run
5. `/gps/*` source commands: General Particle Source configuration
6. `/source/timing/*` commands when `source.timing` is present: time structure
7. `/run/beamOn <N>` when `geant4runner.numberOfParticles` is set: execute beam

These YAMLs are consumed by scripts in:
- [`SimulationSetup/`](../SimulationSetup/README.md)
- [`runSimulation/`](../runSimulation/README.md)
- [`photonTransportation/`](../photonTransportation/README.md)
- [`endToEnd/`](../endToEnd/README.md)
- [`scintillatorCataloging/`](../scintillatorCataloging/README.md)
