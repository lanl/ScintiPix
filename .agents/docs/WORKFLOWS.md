# Workflow overview of ScintiPix      

This document provides an overview of the ScintiPix workflow, from simulation configuration with Pydantic, to Geant4 simulations, to optics transport with RayOptics, photon multiplication in the image intensifier, and finally to sensor readout. 

NOTE [07/08/26]: The optics, intensifier, and sensor stages are still under active development, so this document focuses on the current state of the Geant4 simulation and the intended design for the downstream optics, intensifier, and sensor stages.

ScintiPix is a highly configurable simulation framework. All parameters are defined in a modular Pydantic configuration called `ScintiPixConfig`. This configuration is the single source of truth for all parameters across the workflow, from Geant4 to optics to intensifier to sensor. The Pydantic configuration is designed to be human-friendly and self-documenting, with validation and defaults. 

## Configuration with Pydantic models

The Pydantic configuration is defined in `src/config.py`. The main configuration class is `ScintiPixConfig`, which contains sub-configurations for each stage of the workflow. The configuration can be loaded from a YAML file or constructed programmatically. 

### Sub-routine for lens focusing

Users can define a working distance for the lens model, or have ScintiPix automatically determine the working distance based on the lens prescription and requested FOV. The working distance is the distance from the scintillator back face to the lens entrance plane. It is derived from the absolute geometry coordinates rather than being equal to `optical.interface.position_mm.z_mm`.

To enable automatic lens focusing:
1. Set `metadata.RunControls.auto_focus_lens: true` in your configuration
2. The routine calls `src/optics/focus.py` to determine the optimal working distance, internal lens element positions, and mechanically permitted back focus using RayOptics.
3. The calculated working distance is converted back to the absolute `optical.interface.position_mm.z_mm` coordinate.
4. This positions the optical interface (where photons are recorded) at the correct distance from the scintillator

This is a one-time setup step that should be done before running the Geant4 simulation, since the working distance affects the optical interface position in the Geant4 geometry.

NOTE [07/09/26]: This routine is still under development and may be subject to change. This routine is not required to run the Geant4 simulation, but it is recommended for proper lens focusing in the optics stage.

## Geant4 simulation

The Geant4 simulation runner is defined in `src/runner/runSimulation.py`. The main entry point is the `run_simulation` function, which takes a `Simulation` object (the top-level Pydantic configuration) as input. The Geant4 simulation is configured according to the parameters in the `Simulation` config, including the geometry, materials, physics processes, and scoring. This module outputs binary files containing information on the simulated events, including primary particles, secondary particles, and scintillation photons that reach the optical interface.

The optical interface is a scoring/collection plane positioned between the scintillator back face and the lens system. It captures photons that exit the scintillator and records their position, direction, polarization, time, wavelength, and provenance information (linking back to the primary and secondary particles that generated each photon). This data serves as the handoff point to the downstream optics stage.

The binary output format is described in detail in `.agents/docs/OUTPUT.md`. The runner creates separate output files for primaries, secondaries, and photons, depending on which outputs are enabled in the configuration.

## Optical transport with RayOptics

The optics stage is defined in `src/optics/OpticalTransport.py`. The main entry point is the `transport_optical_photons` function, which takes the Geant4 optical photon output and transports the photons through a selected lens model to the image intensifier photocathode. The lens model is defined by a Zemax `.zmx` prescription, which is loaded through RayOptics. The optics stage outputs the positions and directions of photons that reach the image intensifier photocathode, which serves as the handoff point to the intensifier stage.

NOTE [07/08/26]: The optics stage is still under active development. The current implementation is a placeholder that does not yet fully utilize RayOptics or the new Geant4 output format. 

## Image intensifier

NOTE [07/08/26]: The image intensifier module is under active development. 

## Sensor readout

NOTE [07/08/26]: The sensor readout module is under active development. 
