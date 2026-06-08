# Geant4 Source Timing Examples

These examples are intentionally limited to Geant4 source/neutron timing. They
do not run optical transport, the intensifier model, or Timepix.

The example script accepts one input: a SimConfig YAML path. The default input
is `examples/yamlFiles/pulsed_neutron_source_timing.yaml`.

## Timing Signal

Both YAMLs configure source creation timing internally. ScintiPix assigns that
time to the Geant4 primary vertex, and Geant4 transports each neutron with its
configured kinetic energy. The primary output records only the first
scintillator interaction time:

```text
primary_interaction_time_ns
```

No source creation time, pulse ID, or pulse-relative time is persisted in
`/primaries`.

For the pulsed example, source times cluster inside each pulse window:

```text
creation_time = start_time + pulse_time_offset + random_uniform(0, pulse_time_width)
```

For the continuous example, source times are assigned with fixed event spacing:

```text
creation_time = start_time + event_id * event_spacing
```

Because `/primaries` only contains primaries that created scintillator secondary
activity, recorded interaction-time gaps can include missing non-interacting
events.

## Inputs

- `examples/yamlFiles/pulsed_neutron_source_timing.yaml`: 20 MeV neutron beam
  with `neutrons_per_pulse: 10`, `pulse_period_ns: 1000000.0`,
  `pulse_time_offset_ns: 0.0`, and `pulse_time_width_ns: 270.0`.
- `examples/yamlFiles/continuous_neutron_source_timing.yaml`: same source and
  detector geometry, but with `event_spacing_ns: 100.0`.

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
2. Generates the Geant4 macro.
3. Runs `scintipix`.
4. Reads `/primaries` from the generated HDF5 file.
5. Prints source-time spacing and interaction-delay summaries.

To change the run size or inspect an existing HDF5 file, edit the constants at
the top of `geant4_source_neutron_timing_example.py`.
