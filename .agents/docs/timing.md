# Timing Module

This document covers the general timing framework used in ScintiPix. Becuase the simulation is designed to be modular, each stage has its own timing component with different owners governing the processing of the timing information. This document describes the overall framework and how each stage handles timing.

## Configuration and staging of timing information
ScintiPix loads YAML configuration into the Pydantic `Simulation` model before executing a simulation. This includes timing parameters used across the simulation stages. Geant4 times every event from zero and knows nothing about the `source.timing` block: for each event, the moment its own source fired is time zero, and the interaction time, photon creation times, and photon arrival times are all measured from there. Geant4 carries that event-relative time through primaries, secondaries, and scintillation photons. Photon-production timing is also influenced by `scintillator.properties.optical.timeComponents`. Optical transport propagates photon time to the intensifier input, where parameters such as `decay_fast_ns`
and `decay_slow_ns` for the phosphor stage will influence the timing of the output events. The `source.timing` block is applied last, after the simulation has finished, when every event is placed on a single clock covering the whole run.

## Stage1: Initializing timing information.
Nothing about `source.timing` reaches Geant4. It is read back off the configuration the run saved, once the run is over, so no macro commands carry it and every Geant4 vertex keeps its default time of zero.

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
- `src/output/parquet.py` calculates the number of Geant4 events per
  pulse from `particle_flux`, the circular GPS source area, and
  `pulse_period_ns`.

For continuous sources, the timing information of the primary particles are the following:

- start_time_ns: This is the start time of the first particle
- particle_flux: This is the number of particles per second per square centimeter.

Notes:
- For continuous sources, the particles are emitted continuously over time, so the timing information is used to determine the arrival times of the particles at at the scintillator and subsequent stages of the simulation.
- `src/output/parquet.py` calculates the average event spacing from
  `particle_flux` and the circular GPS source area.
- Pulsed-only fields are optional in `Simulation` and are omitted or set to
  `None`/`null` for continuous sources.

## Stage2: Timing information within the GEANT4 Framework
The GEANT4 framework handles the processing of timing information for all primaries, secondaries, and scintillation photons, with each event timed from its own start. Every binary output file keeps those event-relative times, and so does the transported photon file that optical transport writes from them.

## Stage3: Placing the events on the run clock
Once the run is over, `src/output/parquet.py` reads `source.timing` from the configuration the run saved, decides when in the run each event's source fired, and writes a parquet copy of every stage that records a time:

    time in the run = time assigned to the event + time recorded by Geant4

`run_simulation` always runs this step, whether or not optical transport was enabled. The event times are drawn from random numbers seeded by the run's own name and sub-run number, so repeating the step on the same run reproduces the same times. See `.agents/docs/outputs.md` for the files it writes.
