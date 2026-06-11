# Geant4 Source Timing Examples

These examples are intentionally limited to running the Geant4 simulation with
source/neutron timing configured from YAML. They do not run optical transport,
the intensifier model, or Timepix.

The script accepts one optional input: a SimConfig YAML path. The default input
is `examples/yamlFiles/pulsed_neutron_source_timing.yaml`.

## Timing Signal

Both YAMLs configure source creation timing internally. ScintiPix assigns that
time to the Geant4 primary vertex, and Geant4 transports each neutron with its
configured kinetic energy. The simulation output records primary timing as:

```text
primary_interaction_time_ns
```

No source creation time, pulse ID, or pulse-relative time is persisted in
`/primaries`.

For the pulsed example, `particle_flux`, source radius, and `pulse_period_ns`
derive the number of Geant4 events assigned to each pulse. Source times cluster
inside each pulse window:

```text
creation_time = start_time + pulse_time_offset + random_uniform(0, pulse_time_width)
```

For the continuous example, `particle_flux` and source radius derive fixed event
spacing:

```text
creation_time = start_time + event_id * event_spacing
```

Because `/primaries` only contains primaries that created scintillator secondary
activity, recorded interaction-time gaps can include missing non-interacting
events.

## Inputs

- `examples/yamlFiles/pulsed_neutron_source_timing.yaml`: 20 MeV neutron beam
  with `particle_flux: 79577.47154594767`, `pulse_period_ns: 1000000.0`,
  `pulse_time_offset_ns: 0.0`, and `pulse_time_width_ns: 270.0`.
- `examples/yamlFiles/continuous_neutron_source_timing.yaml`: same source and
  detector geometry, but with `particle_flux: 79577471.54594767`, which derives
  100 ns Geant4 event spacing.

## Run

From the repository root:

```bash
pixi run python examples/sourceTiming/geant4_source_neutron_timing_example.py
```

To choose the pulsed YAML explicitly:

```bash
pixi run python examples/sourceTiming/geant4_source_neutron_timing_example.py \
  examples/yamlFiles/pulsed_neutron_source_timing.yaml
```

To run the continuous YAML:

```bash
pixi run python examples/sourceTiming/geant4_source_neutron_timing_example.py \
  examples/yamlFiles/continuous_neutron_source_timing.yaml
```

The script:

1. Loads the YAML path argument, or the pulsed YAML when no path is given.
2. Runs the simulation through `run_simulation(config)`.
