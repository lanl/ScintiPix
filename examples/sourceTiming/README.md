# Geant4 Source Timing Examples

These examples are intentionally limited to Geant4 source/neutron timing. They
do not run optical transport, the intensifier model, or Timepix.

The example script accepts one input: a SimConfig YAML path. The default input
is `examples/yamlFiles/pulsed_neutron_source_timing.yaml`.

## Timing Signal

Both YAMLs assign `source_time_ns` as the source neutron creation time. Geant4
then transports each neutron with its configured kinetic energy, so the first
scintillator interaction time is recorded in the same global time frame:

```text
primary_interaction_time_ns - source_time_ns
```

That difference is the simulation-side timing signal for neutron flight and
interaction. No pulse ID or pulse-relative time is persisted.

For the pulsed example, source times cluster inside each pulse window:

```text
source_time_ns = pulse_start_time_ns + random_uniform(0, pulse_width_ns)
```

For the continuous example, source times are assigned with fixed event spacing:

```text
source_time_ns = start_time_ns + event_id * event_spacing_ns
```

Because `/primaries` only contains primaries that created scintillator secondary
activity, the printed source-time gaps can be multiples of `event_spacing_ns`
when non-interacting events are absent from the HDF5 table.

## Inputs

- `examples/yamlFiles/pulsed_neutron_source_timing.yaml`: 20 MeV neutron beam
  with `neutrons_per_pulse: 10`, `pulse_period_ns: 1000000.0`, and
  `pulse_width_ns: 270.0`.
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
