# Optics Overview

This note is for future agents working on optical transport.

Last updated: 2026-06-30 15:40 MDT.

For future edits, add an `Added YYYY-MM-DD` line to new design sections so the
age of each decision is visible.

The current source of truth is the Geant4 simulation output. The downstream
Python optics, intensifier, and sensor stages have not yet been updated to the
new Geant4 output path. Do not treat the existing `src/optics/OpticalTransport.py`
as the desired design.

## Current Handoff From Geant4

Geant4 creates and tracks scintillation photons inside the scintillator. Photons
that reach the optical interface are recorded by the optical-interface sensitive
detector.

The optical interface is the Geant4 collection/scoring plane for photons that
reach the lens side of the setup. It can represent the lens entrance plane for
acceptance and validation, but it is not the RayOptics object plane or image
plane. For each detected optical photon, Geant4 records:

- source/provenance IDs
- photon creation position and time
- scintillator exit position, when available
- optical-interface hit position
- optical-interface hit time
- optical-interface direction
- polarization
- energy and wavelength

These photon rows are currently written through the Geant4 binary output path,
normally under:

```text
<run_root>/simulatedPhotons/photons.bin
```

The binary row layout is defined in:

- `sim/include/structures.hh`
- `sim/src/SimIO.cc`

## Intended Optical Transport

The future `OpticalTransport.py` rewrite should start from the current Geant4
photon binary output, build RayOptics rays for photons accepted at the optical
interface, and transport those rays from the scintillator object plane through
the configured lens to the photocathode/input plane of the image intensifier.

The core mapping should stay simple:

```text
Geant4 photon accepted at optical-interface plane
  scintillator-exit position + direction + wavelength + time
        |
        v
RayOptics object-plane ray at scintillator back face
        |
        v
ray optics through configured ZMX lens
        |
        v
intensifier photocathode/input-plane hit
```

The optical transport output should preserve provenance IDs so downstream
stages can link transported photons back to the original Geant4 photon rows.

## Rewrite Boundary

### Scintillation Photons to Transported Photons

Need to rewrite `src/optics/OpticalTransport.py`. 
Currently has a lot of legacy code and AI generated junk code. 
Note: Avoid carrying over old HDF5 assumptions unless they are still explicitly needed.

The new implementation should start from the object-plane/image-plane model
above and answer these implementation questions:

1. How should object-plane rays be reconstructed from scintillator-exit and
   optical-interface records?
2. How should the fixed photocathode/image plane be represented from lens mount
   and passive C-mount adapter metadata?
3. Do we need to configure lens focus or internal gaps from the selected ZMX
   prescription?
4. Do we need a batch processing mechanism to accelerate transport?
5. Where should the optical Pydantic models live within the project?

We need a comprehensive understanding of Ray Optics libraries to accurately model the propagation of photons through the lens system and ensure that the optical transport stage correctly maps optical-interface photons to the intensifier photocathode/input-plane hits.

Keep the transport stage focused on ray optics. 
The photocathode response, MCP/phosphor behavior will be in the intensifier module, while 
sensor readout belongs to the sensor modules.

## Practical RayOptics Transport Setup

Added 2026-06-30 15:40 MDT.

The practical optical problem is:

```text
object plane                    lens model                  image plane
scintillator back face  ->  selected ZMX prescription  ->  photocathode
```

The optical interface should be treated as a Geant4 scoring/collection plane.
It tells us which photons reached the lens side of the setup and provides a
useful acceptance/validation point. It should not define the object plane or the
image plane.

Use this setup flow:

1. Choose the lens `.zmx`/`.smx` files.
2. Define the RayOptics object plane as the scintillator back face.
3. Define the fixed RayOptics image plane as the intensifier photocathode.
4. Set the object gap from the scintillator-back-face to first-lens-surface
   distance.
5. Load the ZMX prescription as the lens surface/gap model.
6. Validate focus with synthetic object-plane ray bundles before bulk transport.
7. Transport real Geant4 photons that were accepted at the optical-interface
   scoring plane.
8. Write transported photocathode hits with the original photon provenance IDs.

For each accepted Geant4 photon, build a RayOptics ray:

```python
pt0 = [scint_exit_x_mm, scint_exit_y_mm, 0.0]
dir0 = normalized photon direction toward the lens
wvl = photon wavelength in nm
```

Then trace:

```text
object plane -> object gap -> lens surfaces/gaps -> fixed image surface
```

The final RayOptics image-surface intersection is the transported photon hit on
the intensifier photocathode. If tracing fails, the ray is vignetted, or the hit
lands outside the active intensifier area, mark the photon as missed rather than
forcing it onto the photocathode.

Focus should be validated before transporting a full Geant4 photon run. The
focus check should sample object points on the scintillator back face, trace ray
bundles through the selected lens model, and measure spot size at the fixed
photocathode plane. If the spot is not minimized at the photocathode, do not move
the photocathode in software; change a real degree of freedom such as
scintillator-to-lens distance, lens focus state, or the selected prescription.

## RayOptics Lens Model Notes

RayOptics uses a sequential optical model:

```text
object surface -> object gap -> lens surfaces/gaps -> image surface
```

The `.zmx` file is the Zemax sequential lens prescription. It defines the
compound lens surfaces, spacings, apertures, glasses, stop, object surface, and
image surface. The `.smx` file is not a second geometric lens prescription. In
RayOptics it is used to restore or substitute glass definitions when the `.zmx`
references glasses that are not available in the installed optical glass
catalogs.

For ScintiPix, a focused-lens implementation should use this mapping:

- scintillator back face = RayOptics object surface
- distance from scintillator back face to first lens surface = object gap
- ZMX prescription = compound lens
- intensifier photocathode = RayOptics image surface

Then each photon becomes an explicit ray:

```python
pt0 = [scint_exit_x_mm, scint_exit_y_mm, 0.0]
dir0 = normalized photon direction in object-space coordinates
wvl = optical_interface_hit_wavelength_nm
```

The optical-interface plane in Geant4 can remain useful as a lens-entrance
detector or validation plane, but it does not have to be the RayOptics object
surface. If the RayOptics object surface is the scintillator back face, use the
recorded scintillator-exit position as the ray start. The ray direction can come
from the recorded photon direction, or be reconstructed from scintillator exit
to the optical-interface hit if that is the more consistent object-space ray
definition.

## Focus And Fixed Intensifier Position

Updated 2026-06-30 15:40 MDT.

The image intensifier input is a C-mount interface and is mechanically fixed to
the back of the selected lens through a passive adapter. The adapter has no glass
or corrective optic, so it adds only mechanical air spacing and optional aperture
limits. It has no optical power.

For C-mount, the standard flange focal distance is 17.526 mm from the C-mount
flange shoulder to the image plane. In this setup, that image plane is the
intensifier photocathode.

That distance is a mechanical flange-to-image-plane distance, not necessarily
the distance from the last optical surface in the `.zmx` prescription to the
photocathode. Do not blindly replace the final RayOptics image gap with
17.526 mm unless the location of the C-mount flange in the optical prescription
is known.

With a fixed intensifier plane, focusing means making the scintillator back face
image onto that fixed plane:

- If the lens has an adjustable focus state, adjust the lens focus/internal
  spacing for the scintillator-to-lens object distance.
- If the lens prescription is fixed-focus, choose the scintillator-to-lens
  distance that focuses onto the fixed intensifier plane.
- If the lens, scintillator, and intensifier are all mechanically fixed,
  RayOptics can evaluate the focus quality but cannot make the system focused
  without changing geometry.

The first implementation should load the `.zmx` with RayOptics, set the object
gap from the scintillator-to-lens geometry, preserve the image plane from the
prescription unless the flange-to-image mapping is known, and trace photon rays
to the final image surface. If needed, use the RayOptics paraxial image distance
as a first estimate, then scan image or object distance around that estimate and
minimize spot size for representative scintillator rays.

## Focusing Routine

The optics module should include a focusing or focus-validation routine that is
independent of a Geant4 photon run. This routine only needs:

- the lens `.zmx`/`.smx` files
- the scintillator back-face/object-plane size
- the scintillator-to-lens geometry
- the fixed intensifier/image-plane geometry

This can be run before a full simulation. Its purpose is to answer whether the
configured optical geometry images the scintillator back face onto the fixed
intensifier plane, and what geometry adjustment would improve focus.

The basic focus metric should be spot size at the fixed image plane:

1. Sample representative object points on the scintillator back face.
2. For each object point, trace a bundle of rays through the lens.
3. Intersect those rays with the fixed intensifier/image plane.
4. Compute RMS spot size for each object point and summarize across the field.

If the RMS spot size is minimized at the fixed intensifier plane, the lens is
focused for that object distance. If the minimum is in front of or behind the
fixed plane, the configured geometry is defocused.

The focusing routine should keep the real mechanical constraints explicit:

- The intensifier is fixed to the back of the lens.
- The Geant4 optical-interface plane is a scoring plane, not necessarily the
  RayOptics object surface.
- The scintillator-to-interface distance is user-configured in the Geant4 setup
  and can represent the real experiment.

Because the Geant4 simulation runs before RayOptics transport, the focus routine
can be used upstream to choose or validate the scintillator-to-interface
distance before generating photon data. The resulting geometry should then be
used consistently in the Geant4 optical-interface placement and the RayOptics
object/image model.

If the lens is not focused with the configured geometry, one of the following
must change:

- the scintillator-to-lens/interface distance
- the lens focus state, if the `.zmx` prescription exposes or can be mapped to
  an internal focusing group/gap
- the lens prescription used for transport

Do not make the photon transport stage responsible for discovering focus during
every run. Transport should use an already selected optical model and move real
Geant4 photon rays through it.

## Geant4 Resolution Target

Add a Geant4-side resolution target as an optional scintillator-back-face mask.
This target is not part of RayOptics. Its purpose is to generate a known spatial
pattern in the optical photons before they are transported through the lens.

The first target should be a Siemens star made from repeated absorbing annular
sectors. Keep this independent from the existing circular `maskRadius`; the
circular mask controls aperture or field, while the Siemens star provides a
resolution pattern.

Suggested initial geometry:

- target type: Siemens star
- inner radius: `1 um`
- outer radius: `100 mm`
- thickness: `1 um`
- line pairs: `64`
- plane: scintillator `+Z` face
- material: reuse the existing highly absorbing mask material

Implement the opaque spokes with `G4Tubs` sectors:

```cpp
auto* wedge = new G4Tubs(
    "SiemensStarWedgeSolid",
    innerRadius,
    outerRadius,
    0.5 * thickness,
    startPhi,
    opaquePhi);
```

For `linePairs = 64`:

```text
pairPhi = 360 deg / linePairs
opaquePhi = 0.5 * pairPhi
startPhi = i * pairPhi
```

Only opaque sectors need physical volumes; the clear sectors are empty space.
Place all sectors as a thin absorber layer centered on the scintillator back
face, with a small clearance so the target does not overlap the scintillator or
the optical-interface scoring volume.

The useful local line-pair pitch varies with radius:

```text
pitch_mm(r) = 2*pi*r_mm / linePairs
```

For `64` line pairs:

- at `100 mm`, pitch is about `9.8 mm`
- at `10 mm`, pitch is about `0.98 mm`
- at `1 mm`, pitch is about `98 um`
- at `0.1 mm`, pitch is about `9.8 um`

Do not over-generalize the first implementation. Add a small set of controls:

- enabled/disabled
- outer radius
- line-pair count

Keep the inner radius and thickness fixed at the default values unless there is
a clear need to expose them. Avoid a generic target-shape framework until the
Siemens star target has been implemented and used.

This resolution target can be toggled on or off within the Simulation model under the geant4runner settings with the `resolutionTargetEnabled` flag.
