# Workflow overview of ScintiPix      

This document provides an overview of the ScintiPix workflow, from simulation configuration with Pydantic, to Geant4 simulations, to optics transport with RayOptics, photon multiplication in the image intensifier, and finally to sensor readout. 

NOTE [07/08/26]: The optics, intensifier, and sensor stages are still under active development, so this document focuses on the current state of the Geant4 simulation and the intended design for the downstream optics, intensifier, and sensor stages.

ScintiPix is configured through the top-level Pydantic `Simulation` model. This model is the single source of truth for parameters across the workflow, from Geant4 to optics, intensifier, and sensor stages.

## Configuration with Pydantic models

The top-level model is defined in `src/models/simulation.py`. YAML is loaded through `src/config/yaml.py` or the public `src.config.yaml.from_yaml(...)` function.

### Sub-routine for lens focusing

Users can define a working distance for the lens model, or have ScintiPix automatically determine the working distance based on the lens prescription and requested FOV. The working distance is the distance from the scintillator back face to the lens entrance plane. It is derived from the absolute geometry coordinates rather than being equal to `optical.interface.position_mm.z_mm`.

The implemented `src/optics/focus.py` routine determines the bounded working
distance, internal lens adjustment, and back focus using RayOptics. It updates
the `Simulation` object directly. Enable it with
`metadata.RunControls.auto_focus_lens: true`.

The runner integration:

1. Call `auto_focus_lens(config)` before macro generation.
2. Use the updated absolute `optical.interface.position_mm.z_mm` coordinate.
3. Preserve the optimized internal focus and back focus on the primary lens.

This is a one-time setup step that should be done before running the Geant4 simulation, since the working distance affects the optical interface position in the Geant4 geometry.

NOTE [07/09/26]: This routine is still under development and may be subject to change. This routine is not required to run the Geant4 simulation, but it is recommended for proper lens focusing in the optics stage.

## Geant4 simulation

The Geant4 simulation runner is defined in `src/runner/runSimulation.py`. The main entry point is the `run_simulation` function, which takes a `Simulation` object (the top-level Pydantic configuration) as input. The Geant4 simulation is configured according to the parameters in the `Simulation` config, including the geometry, materials, physics processes, and scoring. This module outputs binary files containing information on the simulated events, including primary particles, secondary particles, and scintillation photons that reach the optical interface.

The optical interface is a scoring/collection plane positioned between the scintillator back face and the lens system. It captures photons that exit the scintillator and records their position, direction, polarization, time, wavelength, and provenance information (linking back to the primary and secondary particles that generated each photon). This data serves as the handoff point to the downstream optics stage.

The binary output format is described in detail in `.agents/docs/OUTPUT.md`. The runner creates separate output files for primaries, secondaries, and photons, depending on which outputs are enabled in the configuration.

## Optical transport with RayOptics

Updated 2026-07-13.

The binary RayOptics transport stage is implemented in
`src/optics/raytrace.py`. Call `transport_photons(config)` with the same
`Simulation` object used for Geant4 so the autofocus-adjusted working distance,
internal focus adjustment, and back focus are preserved.

The stage reads `simulatedPhotons/photons.bin`, traces from the scintillator
back face through the adjusted primary lens, and writes only photons that reach
the active photocathode area to `transportedPhotons/photons.bin`. It is not yet
called automatically by `src/runner/runSimulation.py`.

## Image intensifier

The active runtime is pending the binary RayOptics transport output. The retired
HDF5 implementation is under `legacy/`.

## Sensor readout

The active runtime is pending the binary intensifier output. The retired HDF5
implementation is under `legacy/`.
