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

This does four things in order:

1. Reads and checks the YAML file.
2. Focuses the lens for the requested 40 x 40 mm patch, and saves the focused settings so the
   run can be repeated exactly.
3. Writes a Geant4 command file and runs the simulator, which records the incident particles
   and the light they produce.
4. Traces that light through the lens and keeps only the photons that land on the
   photocathode.

With the 1000 incident particles the example asks for, this takes under ten seconds. It
produces 19,718 photons leaving the scintillator toward the lens, of which 6,451 reach the
photocathode.

Everything lands in `data/OGS_50mm_AmBe_000/`:

```
config/             the focused settings, so the run can be repeated
macros/             the Geant4 command file that was run
logs/               the simulator's output
primaries/          one record per incident neutron or gamma that deposited energy
secondaries/        particles produced inside the scintillator
simulatedPhotons/   light leaving the scintillator toward the lens
transportedPhotons/ light that reached the photocathode
```

## Step 2: write the photon table

Tracing photons and writing the photon table are separate steps, so the table is written with
its own call. From the top of the repository:

```python
from pathlib import Path
import sys

sys.path.append(str(Path.cwd()))

from src.output.photon_parquet import write_photon_parquet

write_photon_parquet("data/OGS_50mm_AmBe_000")
```

This reads `transportedPhotons/photons.bin` and `primaries/primaries.bin` and writes
`data/OGS_50mm_AmBe_000/photons.parquet`: one row per photon that reached the photocathode.

If you write your own script that runs the simulation and writes the table together, put the
work inside a `main()` function guarded by `if __name__ == "__main__":`, the way
`examples/runSimulation/run_simulation_from_yaml.py` does. Larger runs trace photons across
several processes, and without that guard those processes fail to start.

## The photon table

```
photon_id  x  y  timestamp_canonical  tot  quality_flags  cluster_id  primary_track_id  secondary_track_id  event_type
```

The first six columns are what HERMES writes for real data. The last four are the answer key
and do not exist in real data.

| Column | Meaning |
| --- | --- |
| `photon_id` | Row number, counting from 0. |
| `x`, `y` | Where the photon landed on the photocathode, in millimetres from the centre. |
| `timestamp_canonical` | When the photon landed, counted in HERMES time ticks. One tick is 25 ns divided by 12288, about 2.03 picoseconds. Multiply by that to get nanoseconds. |
| `tot` | Always 0 for now. |
| `quality_flags` | Always 0 for now. |
| `cluster_id` | Which firing of the source this photon belongs to. |
| `primary_track_id` | Which incident particle within that firing: the neutron is 1, its coincident gamma is 2. |
| `secondary_track_id` | Which particle inside the scintillator actually made the light. |
| `event_type` | What the incident particle was: `n` for a neutron, `g` for a gamma. |

`tot` and `quality_flags` are placeholders. In real data they come from the intensifier and
the sensor, and neither of those stages is implemented yet. They are written anyway, as zeros,
so code reading a HERMES table finds the columns it expects.

### What `cluster_id` means

Every time the source fires, the simulator numbers that firing, and that number is copied onto
every photon tracing back to it. So `cluster_id` groups photons by the firing that caused
them. Two photons with the same `cluster_id` came from the same firing; two photons with
different values came from different firings.

This is the answer key for clustering. A clustering algorithm sees only `x`, `y`, and
`timestamp_canonical`, and has to work out which photons belong together. Comparing its groups
against `cluster_id` tells you whether it got it right.

From the example's 1000-particle run: 296 firings produced at least one photon that reached the
photocathode, and those 296 groups hold all 6,451 photons. Group sizes vary widely — half hold
14 photons or fewer, while the largest holds 153. Most firings either send their light outside
the imaged patch or away from the lens, which is why 1000 firings yield 296 groups.

Because `cluster_id` is the firing number, values are not consecutive. A run of 1000 particles
produces values spread across 0 to 999, with gaps where a firing produced no detected light.

### What `event_type` means

`event_type` says what kind of particle arrived: `n` for a neutron, `g` for a gamma. This lets
you check whether a clustering algorithm behaves differently on the two, which matters because
they leave different amounts of light in different patterns.

The labels are short because that is what the simulator writes into `primaries.bin`. Expect
`n` and `g`, not `neutron` and `gamma`.

In the example's 1000-particle run, 6,421 photons were labelled `n` and 30 were labelled `g`.
Gammas are rare in the table even though the source emits one with more than half its
neutrons: a 4.439 MeV gamma usually crosses 20 mm of plastic without depositing enough energy
to make detectable light.

An empty `event_type` means a photon could not be matched back to an incident particle. That
should not happen; if it does, the writer logs a warning saying how many rows are affected.

### A neutron and its gamma share one `cluster_id`

When the source emits a neutron and its coincident gamma, both belong to the same firing, so
photons from both carry the **same** `cluster_id`. They are told apart by `primary_track_id`:
the neutron is 1 and the gamma is 2. The `event_type` is recorded per particle, so the two sets
of rows are correctly labelled `n` and `g` even though they share a `cluster_id`.

This is the interesting case for clustering. The neutron and the gamma start at the same place
at the same time but travel at very different speeds, so their light shows up in two separate
places, often at two separate times, while sharing one `cluster_id`. A clustering algorithm has
to decide whether that is one thing or two. If you want strictly one incident particle per
group, group by `cluster_id` and `primary_track_id` together rather than `cluster_id` alone.

Expect this case to be rare, because it needs both particles to make detectable light. It did
not occur at all in the example's 1000-particle run. A 20,000-particle run with the gamma
forced on every firing produced 8 such groups. One of them looked like this:

```
event_type  primary_track_id  photons  first ns  last ns  mean x  mean y
n           1                       9     11.77   171.08   -3.91    1.13
g           2                      40      1.09   147.13   -4.63    3.60
```

One `cluster_id`, two incident particles, two separate patches of light.

## Reading it into HERMES

HERMES reads a photon table with these columns:

```
photon_id  x  y  timestamp_canonical  tot  quality_flags
```

`photons.parquet` has exactly those, with the same names, units, and order, so HERMES can read
it directly. The four truth columns sit after them and are ignored by code that does not ask
for them.

The usual way to use this is:

1. Hand the first six columns to the clustering code, exactly as if they were real data.
2. Compare the groups it returns against `cluster_id`.
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

- [Workflow overview](./workflows.md) — the stages this example runs through.
- [Simulation outputs](./outputs.md) — the binary files written before the photon table.
- [Autofocus](./autofocus.md) — the lens focusing step.
