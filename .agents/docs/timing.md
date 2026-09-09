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

### Choosing `particle_flux`

`particle_flux` is per square centimetre, so on its own it does not tell you the
rate. The rate depends on how large the source disc is:

    particles per second = particle_flux * pi * (radius_mm / 10)^2

To get a rate you have in mind, divide it by that area. This is where the values
in the examples come from, and it is why they look arbitrary:
`79577.47154594767` from a 2 mm radius disc means 10,000 particles per second,
but from a 10 mm disc the same number would mean 250,000.

### How long a run covers

The flux also sets how much time the run covers, which is worth working out
before starting a long run:

    particles per pulse = ceil(rate * pulse_period_ns / 1e9)

    continuous: span = event count * 1e9 / rate
    pulsed:     span = (event count / particles per pulse) * pulse_period_ns

`pulsed_neutron_source_timing.yaml` fires 5000 events at 10 per pulse with pulses
1 ms apart, so it covers 500 ms. Lowering the flux does not shorten the run; it
spreads the same events over more time.

For continuous sources this is an average, because the gaps between events are
random. The span of any one run scatters around it by roughly one over the square
root of the event count, so the 200-event continuous example lands about 7% out.

## Stage2: Timing information within the GEANT4 Framework
The GEANT4 framework handles the processing of timing information for all primaries, secondaries, and scintillation photons, with each event timed from its own start. Every binary output file keeps those event-relative times, and so does the transported photon file that optical transport writes from them.

## Stage3: Placing the events on the run clock
Once the run is over, `src/output/parquet.py` reads `source.timing` from the configuration the run saved, decides when in the run each event's source fired, and writes a parquet copy of every stage that records a time:

    time in the run = time assigned to the event + time recorded by Geant4

`run_simulation` always runs this step, whether or not optical transport was enabled. The event times are drawn from random numbers seeded by the run's own name and sub-run number, so repeating the step on the same run reproduces the same times. See `.agents/docs/outputs.md` for the files it writes.
