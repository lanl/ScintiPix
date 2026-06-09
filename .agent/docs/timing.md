# Timing Module

This document covers the general timing framework used in ScintiPix. Becuase the simulation is designed to be modular, each stage has its own timing component with different owners governing the processing of the timing information. This document describes the overall framework and how each stage handles timing.

## Configuration and staging of timing information
ScintiPix uses YAML files to load configuration information into pydantic model, `SimConfig` before executing any given simulation. This includes several timing parameters that are used across different stages of the simulation. For example, the `SimConfig` model includes source field that can either be set to continuous or pulsed. This effects how the timing information for the primary particles are initialized in the GEANT4 stage. Once the timing information is initialized, GEANT4 will handle the processing of timing information for all primaries, secondaries, and scintillation photons. Timing of when optical photons are produced are influenced by specific scintillator parameters within `SimConfig`, mainly `timeComponents`. The optical transport stage will then take the timing information from the scintillation photons and propagate it to the input of the intensifier stage. The intensifier stage will then process the timing information of the input photons and produce output events with their own timing information. Here intersifier parameters in `SimConfig` such as `decay_fast_ns`
and `decay_slow_ns` for the phosphor stage will influence the timing of the output events.

## Stage1: Initializing timing information. 
Before the GEANT4 simulation stage, global timing information needs to be configured and initialized. This is done through the `SimConfig` model, where users can specify the source type (continuous or pulsed) and other relevant timing parameters. Based on this configuration, the timing information for the primary particles will be passed to the GEANT4 stage through the messager module of the GEANT4 code. 

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

For continuous sources, the timing information of the primary particles are the following:

- start_time_ns: This is the start time of the first particle
- particle_flux: This is the number of particles per second per square centimeter.l

Notes:
- For continuous sources, the particles are emitted continuously over time, so the timing information is used to determine the arrival times of the particles at at the scintillator and subsequent stages of the simulation.
- All the timing fields for pulsed sources are present in the `SimConfig` model, but they are set to `None` or 'null' when the source type is set to continuous.