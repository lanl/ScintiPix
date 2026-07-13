# Autofocus with Optical Transport Example

This example demonstrates the complete workflow for automatic lens focusing followed by Geant4 simulation and optical transport through the lens system.

## Overview

The workflow includes four stages:

1. **Automatic Lens Focusing** - Optimizes working distance, internal lens adjustment, and back focus using RayOptics
2. **Configuration Saving** - Saves the optimized configuration to a YAML file for reference and reproducibility
3. **Geant4 Simulation** - Simulates neutron interactions and scintillation photon generation
4. **Optical Transport** - Traces photons through the lens system to the image intensifier photocathode

## Running the Simulation

### Basic Usage

```bash
pixi run python examples/autofocus/run_autofocus_with_transport.py
```

This will use the default configuration: `examples/yamlFiles/EJ200_siemens_50mm.yaml`

### Custom Configuration

```bash
pixi run python examples/autofocus/run_autofocus_with_transport.py path/to/your/config.yaml
```

## Analyzing an Existing Run

After the simulation finishes, generate the scintillator-exit and photocathode
images separately:

```bash
pixi run python examples/autofocus/analyze_autofocus_output.py
```

Use the same YAML path when running a custom configuration:

```bash
pixi run python examples/autofocus/analyze_autofocus_output.py path/to/your/config.yaml
```

The analysis reads the existing photon binaries. It does not run autofocus,
Geant4, or optical transport again.

## Example Configuration

The default configuration (`EJ200_siemens_50mm.yaml`) demonstrates:

- **Scintillator**: EJ200, 100×100×20 mm with 40×40 mm field of view
- **Lens**: Canon EF 50mm f/1.0L (from catalog)
- **Intensifier**: Cricket2 with 18 mm image circle
- **Source**: 6 MeV neutrons, pulsed mode, 50,000 particles
- **Siemens Star**: Resolution target enabled for optical performance evaluation

### Autofocus Parameters

The autofocus routine searches within these bounds:

- **Working distance**: 180-250 mm (scintillator back face to lens entrance)
- **Focus adjustment**: -3.0 to 3.0 mm (internal lens element spacing)
- **Back focus**: 48.0 to 52.0 mm (lens exit to photocathode)

## Output Files

The simulation and analysis scripts write the following outputs under
`data/{SimulationRunID}_{SubRunNumber:03d}/`:

### Configuration
- `config/{RunID}_000_focused.yaml` - Optimized lens configuration with `auto_focus_lens: false`

### Geant4 Outputs
- `primaries/primaries.bin` - Primary particle information
- `secondaries/secondaries.bin` - Secondary particle information
- `simulatedPhotons/photons.bin` - Scintillation photons at the optical interface

### Optical Transport Outputs
- `transportedPhotons/photons.bin` - Photons that successfully reach the photocathode

### Analysis Outputs
- `scintillator_exit.png` - Photon positions at the scintillator exit
- `photocathode_image.png` - Transported photon positions at the photocathode

### Logs and Macros
- `logs/runLog.txt` - Complete simulation log
- `macros/{RunID}_000.mac` - Generated Geant4 macro

## What the Autofocus Does

The automatic lens focusing routine:

1. **Loads the lens prescription** from the catalog ZMX file
2. **Defines optimization objectives**:
   - Minimize RMS spot size across the field of view
   - Keep all rays within the photocathode active area
3. **Searches the parameter space** using bounded optimization
4. **Updates the configuration** with optimal values:
   - `optical.interface.position_mm.z_mm` (working distance)
   - `optical.lenses[primary].focus_adjustment_mm` (internal focus)
   - `optical.lenses[primary].back_focus_mm` (back focal distance)
5. **Saves the focused configuration** for reproducibility

## Understanding the Output

### Autofocus Results

Check the log for lines like:
```
Autofocus complete: working distance=180.000 mm, focus adjustment=-2.999 mm, 
back focus=50.463 mm, worst RMS spot=0.038 mm, image radius=7.104 mm
```

- **Working distance**: Distance from scintillator back to lens entrance
- **Focus adjustment**: Internal lens element spacing adjustment
- **Back focus**: Distance from lens exit to photocathode
- **Worst RMS spot**: Largest RMS spot size across the field (quality metric)
- **Image radius**: Maximum radial extent of the focused image

### Photon Statistics

The transport stage will log:
- Number of photons read from Geant4 simulation
- Number of photons that reach the photocathode
- Output file location and size

## Reusing the Focused Configuration

The saved `*_focused.yaml` file has `auto_focus_lens: false` to prevent re-running the optimization. To use it:

```bash
pixi run python examples/autofocus/run_autofocus_with_transport.py \
    data/EJ200_siemens_50mm_000/config/EJ200_siemens_50mm_000_focused.yaml
```

This will skip autofocus and use the pre-optimized lens parameters directly.

## Customizing the Example

### Changing the Lens

Edit the YAML to use a different lens from the catalog:

```yaml
optical:
  lenses:
    - catalogId: YourLensModel
      primary: true
      focusAdjustmentBoundsMm: [-5.0, 5.0]  # Adjust bounds as needed
      backFocusBoundsMm: [40.0, 60.0]
```

### Adjusting Search Bounds

If autofocus fails to converge, try widening the search bounds:

```yaml
optical:
  interface:
    workingDistanceBoundsMm: [150.0, 300.0]  # Wider range
  lenses:
    - focusAdjustmentBoundsMm: [-10.0, 10.0]
      backFocusBoundsMm: [30.0, 70.0]
```

### Disabling Stages

To run only certain stages, modify the `RunControls`:

```yaml
metadata:
  RunControls:
    auto_focus_lens: true      # Run autofocus
    geant4_simulation: true    # Run Geant4
    transportation: false      # Skip optical transport
    intensification: false     # Skip intensifier
    sensor_detection: false    # Skip sensor
```

## Requirements

- Geant4 binary built and available as `scintipix`
- Lens prescription file (ZMX format) in the catalog
- RayOptics installed (via pixi)
- Python 3.11+

## See Also

- Main documentation: `../../.agents/docs/WORKFLOWS.md`
- Configuration reference: `../../.agents/docs/`
- Lens catalog: `../../catalogs/lenses/catalog.yaml`
- Other examples: `../runSimulation/`, `../sourceTiming/`
