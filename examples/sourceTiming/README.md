# Source Timing Examples

These examples run the Geant4 simulation with source timing configured from
YAML. They do not run optical transport, the intensifier model, or Timepix.

The script accepts one optional input: a `Simulation` YAML path. The default input
is `examples/yamlFiles/pulsed_neutron_source_timing.yaml`.

## Timing Signal

Geant4 times every event from its own start, so `primaries.bin` holds
`primary_interaction_time_ns` measured from the moment that event's source
fired. Nothing in the YAML changes that.

After the run, `src/output/parquet.py` works out when in the run each event
fired and writes `primaries/primaries.parquet` with those times added:

    time in the run = event_time_ns + time from primaries.bin

For the pulsed example, `particle_flux`, the source area, and `pulse_period_ns`
give the number of events per pulse, and each event lands at a random point
inside its own pulse window:

```text
event_time_ns = start_time + pulse_id * pulse_period
                + pulse_time_offset + random_uniform(0, pulse_time_width)
```

For the continuous example, `particle_flux` and the source area give the average
gap between events. The gaps themselves are random, the way a steady source
arrives:

```text
event_time_ns = start_time + running total of random gaps
```

`primaries` only records primaries that produced secondary activity in the
scintillator, so events that did not interact leave gaps in the times.

## Inputs

Both fire a 20 MeV neutron beam from a 2 mm radius disc, which is 0.1257 square
centimetres.

- `examples/yamlFiles/pulsed_neutron_source_timing.yaml`:
  `particle_flux: 79577.47154594767`, so 10,000 neutrons per second and 10 in
  each 1 ms pulse. Pulses are 270 ns wide.
- `examples/yamlFiles/continuous_neutron_source_timing.yaml`: same geometry with
  `particle_flux: 79577471.54594767`, so 10 million neutrons per second and an
  average gap of 100 ns.

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
2. Runs the simulation through `run_simulation(config)`, which writes
   `primaries/primaries.parquet` at the end.

To see the time structure, plot that file:

```bash
pixi run python examples/analysis/plotting/plot_primaries_toa.py \
  data/pulsed_neutron_source_timing_000 --range 0 5000000 --bins 200
```
