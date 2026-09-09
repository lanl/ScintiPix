# Example: OGS scintillator, 50 mm lens, AmBe source

This walks through `examples/yamlFiles/OGS_50mm_AmBe.yaml` end to end and explains how to read
the photon table it produces. The point of the example is to generate scintillation photons
whose cause is known, so photon-clustering code can be checked against an answer key instead
of being eyeballed.

## What the example simulates

An AmBe source sits 100 mm in front of a 100 x 100 x 20 mm Organic Glass Scintillator. The
source emits neutrons in all directions, with energies drawn from the measured AmBe energy
spectrum committed under `catalogs/sources/AmBe/`. About 58% of the time it also emits the
4.439 MeV gamma that comes with an AmBe neutron. Neutrons and gammas deposit energy in the
scintillator, the scintillator gives off light, and a Canon EF 50 mm f/1.0L lens images the
back face of the scintillator onto the photocathode of an intensifier.

The scintillator, the source, and the lens are all named rather than spelled out:

```yaml
scintillator:
  catalogId: OGS
source:
  catalogId: AmBe
optical:
  lenses:
    - catalogId: CanonEF50mmf1.0L
```

Loading the file fills in the rest from `catalogs/`. For the source, that means the particle
(neutron), the emission in all directions, the energy spectrum, and the coincident gamma. The
only thing the example states about the source is where it sits.

Two settings are worth knowing about, because changing either can break the run:

- **`fieldOfView` is 40 x 40 mm.** The lens can only image a patch of the scintillator onto
  the 18 mm photocathode circle. The full 100 x 100 mm face does not fit, so the example asks
  for a 40 x 40 mm patch in the middle. Widen this too far and the lens focusing step fails,
  because no working distance produces an image that small.
- **`auto_focus_lens: true` is required for photon tracing.** Tracing photons through the lens
  needs a focused lens, and the focusing step is what computes the working distance and back
  focus. Turning focusing off while leaving tracing on will fail.

## Before you run

Build the simulator once:

```bash
pixi run build-sim
```

## Step 1: run the simulation

```bash
pixi run python examples/runSimulation/run_simulation_from_yaml.py \
    examples/yamlFiles/OGS_50mm_AmBe.yaml
```

This does five things in order:

1. Reads and checks the YAML file.
2. Focuses the lens for the requested 40 x 40 mm patch, and saves the settings it will use so
   the configuration can be reviewed or rerun. Fresh Geant4 random seeds mean
   that identical photon output is not guaranteed.
3. Writes a Geant4 command file and runs the simulator, which records the incident particles
   and the light they produce.
4. Traces that light through the lens and keeps only the photons that land on the
   photocathode.
5. Places every event on one clock covering the whole run and writes the parquet tables.

The run time and photon counts depend on the machine, random seeds, and the
configuration. Treat any counts or timings from a particular run as illustrative,
not as fixed expected output.

Everything lands in `data/OGS_50mm_AmBe_000/`:

```
config/             the settings the run used, so it can be repeated
macros/             the Geant4 command file that was run
logs/               the simulator's output
photons.parquet     one row per photon that reached the photocathode
primaries/          one record per incident neutron or gamma that deposited energy
secondaries/        particles produced inside the scintillator
simulatedPhotons/   light leaving the scintillator toward the lens
transportedPhotons/ light that reached the photocathode
```

The `.bin` files hold the times Geant4 recorded, each measured from the start of its own event.
The `.parquet` files alongside them hold the same times moved onto one clock covering the whole
run. See `.agents/docs/outputs.md` for the full list.

If you write your own script that runs the simulation, put the work inside a `main()` function
guarded by `if __name__ == "__main__":`, the way
`examples/runSimulation/run_simulation_from_yaml.py` does. Larger runs trace photons across
several processes, and without that guard those processes fail to start.

## The photon table

```
photon_id  x  y  timestamp_canonical  tot  quality_flags  event_id  event_type
```

The first six columns are what HERMES writes for real data. The last two are the answer key
and do not exist in real data.

| Column | Meaning |
| --- | --- |
| `photon_id` | Row number, counting from 0. |
| `x`, `y` | Where the photon landed on the photocathode, in millimetres from the centre. |
| `timestamp_canonical` | When the photon landed, counted in HERMES time ticks. One tick is 25 ns divided by 12288, about 2.03 picoseconds. Multiply by that to get nanoseconds. |
| `tot` | Always 0 for now. |
| `quality_flags` | Always 0 for now. |
| `event_id` | Which firing of the source this photon belongs to. |
| `event_type` | What the incident particle was: `n` for a neutron, `g` for a gamma. |

`tot` and `quality_flags` are placeholders. In real data they come from the intensifier and
the sensor, and neither of those stages is implemented yet. They are written anyway, as zeros,
so code reading a HERMES table finds the columns it expects.

Nothing else is in the table. `transportedPhotons/photons.bin` holds more about each photon,
including which particle inside the scintillator made it, if you need to go further than the
two answer-key columns.

### What `event_id` means

Every time the source fires, the simulator numbers that firing, and that number is copied onto
every photon tracing back to it. So `event_id` groups photons by the firing that caused them.
Two photons with the same `event_id` came from the same firing; two photons with different
values came from different firings.

This is the answer key for clustering. A clustering algorithm sees only `x`, `y`, and
`timestamp_canonical`, and has to work out which photons belong together. Comparing its groups
against `event_id` tells you whether it got it right.

The number of firings that produce detected light and the group-size distribution
vary with the run. Most firings can produce no transported photons because light
may leave the imaged patch or miss the lens, so a run's particle count and photon
count should not be treated as a fixed one-to-one relationship.

Because `event_id` is the firing number, values are not consecutive. A run of 1000 particles
produces values spread across 0 to 999, with gaps where a firing produced no detected light.

### What `event_type` means

`event_type` says what kind of particle arrived: `n` for a neutron, `g` for a gamma. This lets
you check whether a clustering algorithm behaves differently on the two, which matters because
they leave different amounts of light in different patterns.

The labels are short because that is what the simulator writes into `primaries.bin`. Expect
`n` and `g`, not `neutron` and `gamma`.

Gamma-labeled rows may be less common than neutron-labeled rows because a
4.439 MeV gamma can cross 20 mm of plastic without depositing enough energy to
make detectable light. The exact balance depends on the run configuration and
random sampling.

An empty `event_type` means a photon could not be matched back to an incident particle. That
should not happen; if it does, the writer logs a warning saying how many rows are affected.

### A neutron and its gamma share one `event_id`

When the source emits a neutron and its coincident gamma, both belong to the same firing, so
photons from both carry the **same** `event_id`. `event_type` is recorded per particle, so the
two sets of rows are still correctly labelled `n` and `g`, and grouping by `event_id` and
`event_type` together separates them.

This is the interesting case for clustering. The neutron and the gamma start at the same place
at the same time but fly off in unrelated directions, so they can deposit energy in different
parts of the scintillator and their light can show up in two separate places while sharing one
`event_id`. The measured separation depends on the sampled deposits, lens settings, and run
seed. The gamma can arrive first because it reaches its deposit sooner than the neutron; that
timing difference is separate from the spatial separation on the photocathode.

A clustering algorithm has to decide whether that is one thing or two.

Expect this case to be rare, because it needs both particles to make detectable light. When both particles produce detectable light, one `event_id` can contain two
particle labels and two patches. The exact frequency and measured values depend
on the source sampling and run configuration, so use a saved run artifact when
checking a numerical example.

## Reading it into HERMES

HERMES reads a photon table with these columns:

```
photon_id  x  y  timestamp_canonical  tot  quality_flags
```

`photons.parquet` has exactly those, with the same names, units, and order, so HERMES can read
it directly. `event_id` and `event_type` sit after them and are ignored by code that does not
ask for them.

The usual way to use this is:

1. Hand the first six columns to the clustering code, exactly as if they were real data.
2. Compare the groups it returns against `event_id`.
3. Split that comparison by `event_type` to see how it does on neutrons against gammas.

Two things to keep in mind when comparing against real HERMES data. `tot` and `quality_flags`
are zeros here, so anything reading them sees nothing useful. And these photons have not been
through an intensifier or a sensor, so there is no gain spread, no dead time, and no readout
noise. This table is the light arriving at the photocathode, not what a camera would report.

## Making a bigger run

Raise `geant4runner.numberOfParticles` for more statistics. Run time and output size are both
roughly linear in that number. To keep runs side by side rather than overwriting each other,
change `metadata.RunEnvironment.SimulationRunID`, which names the output directory.

## Related documents

- [Workflow overview](./WORKFLOWS.md) — the stages this example runs through.
- [Simulation outputs](./outputs.md) — the binary files written before the photon table.
- [Autofocus](./AUTOFOCUS.md) — the lens focusing step.
