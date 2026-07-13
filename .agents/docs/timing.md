# Timing Module

This document covers the general timing framework used in ScintiPix. Becuase the simulation is designed to be modular, each stage has its own timing component with different owners governing the processing of the timing information. This document describes the overall framework and how each stage handles timing.

## Configuration and staging of timing information
ScintiPix loads YAML configuration into the Pydantic `Simulation` model before executing a simulation. This includes timing parameters used across the simulation stages. The `source.timing` block selects continuous or pulsed source timing for Geant4 primary vertices. Geant4 then transports timing for primaries, secondaries, and scintillation photons. Photon-production timing is also influenced by `scintillator.properties.optical.timeComponents`. Optical transport propagates photon time to the intensifier input, where parameters such as `decay_fast_ns`
and `decay_slow_ns` for the phosphor stage will influence the timing of the output events.

## Stage1: Initializing timing information. 
Before the Geant4 stage, timing is configured through `Simulation.source.timing`. The Python configuration layer emits the corresponding macro commands through the Geant4 messenger interface.

### Pulsed vs Continuous Sources
For pulsed sources, the timing information of the primary particles are the following: 

- start_time_ns: This is the start time of the first particle
- particle_flux: This is the number of particles per second per square centimeter.
- pulse_period_ns: This is the period of each pulse
- pulse_time_offset_ns: This is the time offset for each pulse 
- pulse_time_width_ns: This is the width of each pulse
- pulse_shape: This is the shape of each pulse

Notes:
- For pulsed sources, the number of neutrons per pulse can be calculated from the neutron flux and the pulse period. 
- The Python configuration layer calculates the number of Geant4 events per
  pulse from `particle_flux`, the circular GPS source area, and
  `pulse_period_ns`.

For continuous sources, the timing information of the primary particles are the following:

- start_time_ns: This is the start time of the first particle
- particle_flux: This is the number of particles per second per square centimeter.

Notes:
- For continuous sources, the particles are emitted continuously over time, so the timing information is used to determine the arrival times of the particles at at the scintillator and subsequent stages of the simulation.
- The Python configuration layer calculates the Geant4 event spacing from
  `particle_flux` and the circular GPS source area.
- Pulsed-only fields are optional in `Simulation` and are omitted or set to
  `None`/`null` for continuous sources.

## Stage2: Timing information within the GEANT4 Framework
Once the timing information is initialized and passed to the GEANT4 stage, the GEANT4 framework will handle the processing of timing information for all primaries, secondaries, and scintillation photons. 
