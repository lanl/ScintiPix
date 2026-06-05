# Example YAML Files

This folder contains shared `SimConfig` YAML inputs used by the scripts under
`examples/`. The authoritative schema is defined in
`src/config/SimConfig.py`; this README is the user-facing field guide for the
same structure.

Current files:
- `CanonEF50mmf1p0L_example.yaml`: primary end-to-end example configuration
- `continuous_neutron_source_timing.yaml`: lightweight continuous source timing
  example for Geant4 `/primaries` timing. Uses fixed `event_spacing_ns`.
- `EJ200.yaml`: catalog-driven scintillator example with overrides
- `EJ276D.yaml`: catalog-driven EJ-276D timing-component example
- `pulsed_neutron_source_timing.yaml`: lightweight pulsed source timing example
  for Geant4 `/primaries` timing. Uses `neutrons_per_pulse`, `pulse_period_ns`,
  and `pulse_width_ns`.
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

`SimConfig` rejects unknown keys inside recognized config blocks. Use the field
names below, or the listed aliases where provided. Extra top-level keys are
ignored by `ConfigIO.from_yaml(...)` so script-specific payloads can coexist
with the strict simulation config.

Relative paths in run-environment settings are resolved by the configuration
helpers before macro writing and pipeline execution.

## Top-Level Blocks

Required:
- `scintillator`: scintillator geometry and material/optical properties
- `source`: Geant4 GPS source settings and optional source timing
- `optical`: lens and optical-interface geometry assumptions
- `Metadata`: run metadata and output directory layout

Optional:
- `intensifier`: image-intensifier model and response parameters
- `sensor`: Timepix sensor/readout parameters
- `simulation`: Geant4 run controls and beam count
- `runner`: Python launcher settings

## `scintillator`

Defines scintillator size, position, mask, and material properties.

Fields:
- `catalogId`: optional scintillator catalog identifier. When present,
  `ConfigIO.from_yaml(...)` hydrates missing `properties` fields from the
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
- `photonEnergy`: photon-energy table in eV; length must match `nKEntries`
- `rIndex`: refractive-index table; length must match `nKEntries`
- `nKEntries`: number of optical table entries; must be greater than zero
- `timeComponents`: scintillation decay profiles

Optional:
- `absLength`: absorption-length table in cm; if present, length must match
  `nKEntries`
- `scintSpectrum`: emission-spectrum table; if present, length must match
  `nKEntries`
- `density`: density in g/cm3; must be greater than zero
- `carbonAtoms`: stoichiometric carbon atom count; must be greater than zero
- `hydrogenAtoms`: stoichiometric hydrogen atom count; must be greater than zero
- `scintYield`: scintillation yield in photons/MeV; must be greater than zero
- `resolutionScale`: Geant4 scintillation resolution scale; must be greater
  than zero

### `scintillator.properties.timeComponents`

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
    event_spacing_ns: 100.0
```

Fields:
- `event_spacing_ns`: required for `continuous`; source-time spacing between
  consecutive Geant4 event IDs. Must be greater than zero. Accepted aliases
  include `eventSpacingNs` and `eventSpacing`.

Pulsed mode:

```yaml
source:
  timing:
    mode: pulsed
    start_time_ns: 0.0
    pulse_period_ns: 1000000.0
    neutrons_per_pulse: 10
    pulse_width_ns: 270.0
    pulse_shape: uniform
```

Fields:
- `pulse_period_ns`: required for `pulsed`; time between pulse starts. Must be
  greater than zero. Accepted aliases include `pulsePeriodNs` and `pulsePeriod`.
- `neutrons_per_pulse`: required for `pulsed`; number of Geant4 events assigned
  to one pulse ID. Must be greater than zero. Accepted alias:
  `neutronsPerPulse`.
- `pulse_width_ns`: required for `pulsed`; neutron creation times are randomly
  distributed over this window during Geant4 primary generation. Must be
  non-negative. Accepted aliases include `pulseWidthNs` and `pulseWidth`.
- `pulse_shape`: currently only `uniform` is accepted. Accepted alias:
  `pulseShape`.

Pulsed event grouping uses:

```text
pulse_id = event_id // neutrons_per_pulse
pulse_start_time_ns = start_time_ns + pulse_id * pulse_period_ns
source_time_ns = pulse_start_time_ns + random_uniform(0, pulse_width_ns)
```

Geant4 transport then determines the relativistic neutron time of flight to the
scintillator interaction.

The simulation persists the assigned source creation time as
`source_time_ns` in `/primaries`. Pulse ID and pulse-relative time are not
persisted; they are intermediate values used only to compute `source_time_ns`.

## `optical`

Defines the primary optical lens and the Geant4 optical-interface plane used as
input to downstream optical transport.

Fields:
- `lenses`: required list of lens descriptors. Exactly one lens must have
  `primary: true`.
- `geometry`: required optical envelope values.
- `sensitiveDetectorConfig`: required optical-interface detector placement.
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
  hydrated by `ConfigIO.from_yaml(...)`.
- `zmxFile`: optional Zemax lens file path or catalog-resolved filename.
- `smxFile`: optional rayoptics sidecar file path or catalog-resolved filename.

### `optical.geometry`

Fields:
- `entranceDiameter`: lens entrance diameter in mm; must be greater than zero.
- `sensorMaxWidth`: sensor maximum width in mm; must be greater than zero.

### `optical.sensitiveDetectorConfig`

Fields:
- `position_mm`: optical-interface center position in mm.
  - `x_mm`
  - `y_mm`
  - `z_mm`
- `shape`: detector shape string.
- `diameterRule`: expression-like sizing rule used by command-generation code,
  for example `min(entranceDiameter,sensorMaxWidth)`.

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

## `simulation`

Optional Geant4 run-control block. If present, it must include
`numberOfParticles` and/or `runtimeControls`.

Fields:
- `numberOfParticles`: optional `/run/beamOn` particle count. Must be greater
  than zero.
- `runtimeControls`: optional macro preamble controls.

### `simulation.runtimeControls`

If present, at least one field must be set.

Fields:
- `controlVerbose`: `/control/verbose`; must be non-negative.
- `runVerbose`: `/run/verbose`; must be non-negative.
- `eventVerbose`: `/event/verbose`; must be non-negative.
- `trackingVerbose`: `/tracking/verbose`; must be non-negative.
- `printProgress`: `/run/printProgress`; must be greater than zero.
- `storeTrajectory`: `/tracking/storeTrajectory`; boolean.

## `runner`

Optional Python-side process-launch settings. These do not map directly to
Geant4 macros.

Fields:
- `binary`: scintipix executable command. Defaults to `scintipix` and must not
  be blank.
- `showProgress`: Python runner progress display flag. Defaults to `false`.
- `verifyOutput`: check for expected HDF5 output after simulation. Defaults to
  `true`.

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
`ConfigIO.macro_commands(...)` emits commands in this order:

1. `simulation.runtimeControls`: runtime parameters and verbosity settings
2. `/output/*` commands from `Metadata.RunEnvironment`: output directory setup
3. scintillator and optical-interface geometry/material commands: physics models
4. `/run/initialize`: initialize the Geant4 run
5. `/gps/*` source commands: General Particle Source configuration
6. `/source/timing/*` commands when `source.timing` is present: time structure
7. `/run/beamOn <N>` when `simulation.numberOfParticles` is set: execute beam

These YAMLs are consumed by scripts in:
- [`SimulationSetup/`](../SimulationSetup/README.md)
- [`runSimulation/`](../runSimulation/README.md)
- [`photonTransportation/`](../photonTransportation/README.md)
- [`endToEnd/`](../endToEnd/README.md)
- [`scintillatorCataloging/`](../scintillatorCataloging/README.md)
