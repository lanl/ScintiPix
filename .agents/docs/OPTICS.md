# Optics Overview

Last updated: 2026-06-30 15:52 MDT.

For future edits, add an `Added YYYY-MM-DD` or `Updated YYYY-MM-DD` line to any
section where the design changes materially.

This note is for future agents working on ScintiPix optical transport. Keep this
module focused on ray optics. Photocathode response, MCP/phosphor behavior, and
sensor readout belong to the intensifier and sensor modules.

The current source of truth is the Geant4 simulation output. The downstream
Python optics, intensifier, and sensor stages have not yet been fully updated to
the new Geant4 output path. Do not treat the existing
`src/optics/OpticalTransport.py` as the desired design.

## What Is This?

Added 2026-06-30.

The optics stage should transport Geant4 optical photons through a selected lens
model to the image intensifier photocathode.

The physical mapping is:

```text
object plane                    lens model                  image plane
scintillator back face  ->  selected ZMX prescription  ->  photocathode
```

The coordinate roles are:

- Object plane: scintillator back face.
- Optical interface: Geant4 collection/scoring plane for photons that reach the
  lens side of the setup. This is useful for acceptance and validation, but it is
  not the RayOptics object plane or image plane.
- Lens model: selected Zemax `.zmx` prescription loaded through RayOptics.
- Image plane: image intensifier photocathode.

RayOptics uses a sequential model:

```text
object surface -> object gap -> lens surfaces/gaps -> image surface
```

For ScintiPix, this should mean:

```text
RayOptics object surface = scintillator back face
RayOptics object gap     = scintillator back face to first lens surface
RayOptics lens model     = selected ZMX prescription
RayOptics image surface  = intensifier photocathode
```

The `.zmx` file is the lens prescription. The `.smx` sidecar is only for glass
restoration/substitution during RayOptics import; it is not a second geometry
model.

## Current Geant4 Handoff

Updated 2026-06-30.

Geant4 creates and tracks scintillation photons inside the scintillator. Photons
that reach the optical interface are recorded by the optical-interface sensitive
detector.

For each detected optical photon, Geant4 records:

- source/provenance IDs
- photon creation position and time
- scintillator exit position, when available
- optical-interface hit position
- optical-interface hit time
- optical-interface direction
- polarization
- energy and wavelength

The photon output schema is defined in:

- `sim/include/structures.hh`
- `sim/src/SimIO.cc`

The transport rewrite should start from the current Geant4 photon output format.
Avoid carrying over old HDF5 assumptions unless the current output path still
explicitly needs them.

## How It Should Be Implemented

Added 2026-06-30.

Use this setup flow:

1. Choose the primary lens `.zmx` and optional `.smx` files from `SimConfig`.
2. Load the ZMX prescription with RayOptics.
3. Define the object plane as the scintillator back face.
4. Set the RayOptics object gap from the scintillator-back-face to first-lens
   surface distance.
5. Define the fixed image plane as the intensifier photocathode.
6. Validate focus with synthetic object-plane ray bundles before bulk transport.
7. Transport real Geant4 photons that were accepted at the optical-interface
   scoring plane.
8. Write transported photocathode hits with original photon provenance IDs.

For each accepted photon, build a RayOptics ray from the object plane:

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

The optical-interface record should still be used. It proves the photon reached
the lens-side collection plane and can help reconstruct or validate the object
space ray, but it should not replace the scintillator back face as the object
plane.

## C-Mount Image Plane

Added 2026-06-30. Updated 2026-07-12.

The image intensifier input is always C-mount and is mechanically fixed to the
back of the selected lens through a passive adapter. The adapter has no glass or
corrective optic, so it adds only mechanical air spacing and possible aperture
limits. It has no optical power.

For C-mount, the flange focal distance is:

```text
C-mount flange shoulder -> image plane = 17.526 mm
```

In this setup:

```text
image plane = intensifier photocathode
```

Do not blindly replace the final RayOptics image gap with `17.526 mm`. That
distance is measured from the C-mount flange shoulder, not from the last optical
surface in the ZMX prescription. To set the image plane from adapter geometry, we
need to know where the lens mount/flange reference is relative to the RayOptics
prescription.

For a passive mount adapter:

```text
native lens flange -> adapter -> C-mount flange -> photocathode
```

If the adapter is the correct fixed length, the photocathode should sit at the
native lens image plane. The transport code should treat this as a fixed
mechanical image plane, not a focusing degree of freedom.

The lens configuration records the net prescription-to-image geometry:

- `backFocusMm`: distance from the last modeled optical surface to the
  photocathode.
- `backFocusBoundsMm`: physically attainable interval imposed by the lens
  mount, adapter, and intensifier interface.
- `focusAdjustmentBoundsMm`: permitted internal focus travel.
- `workingDistanceBoundsMm`: permitted scintillator-to-lens travel, stored on
  the optical interface.

The photocathode remains the image plane. When back focus is adjustable, the
physical lens or adapter spacing changes relative to that plane; the optimizer
does not move the photocathode in software. Without `backFocusBoundsMm`, the
configured back focus is fixed. Autofocus must not create generic bounds.

## Focus Validation

Added 2026-06-30. Updated 2026-07-12.

Focus validation should be a separate optics routine that can run before a full
Geant4 photon simulation.

Inputs:

- lens `.zmx` and optional `.smx` files
- scintillator back-face size
- scintillator-to-lens geometry
- fixed photocathode/image-plane geometry
- mechanically attainable back-focus bounds, when the assembly is adjustable

Basic metric:

1. Sample representative object points on the scintillator back face.
2. Trace a ray bundle from each object point through the selected lens model.
3. Intersect rays with the fixed photocathode plane.
4. Compute RMS spot size for each object point and summarize across the field.

If the spot size is minimized at the photocathode plane, the geometry is focused.
If the minimum is in front of or behind the photocathode, the configured geometry
is defocused.

Do not make bulk photon transport responsible for discovering focus during every
run. If the system is out of focus, change a real degree of freedom:

- scintillator-to-lens distance
- lens focus state/internal gap, if represented in the prescription
- lens-to-photocathode back focus, only within documented mechanical bounds
- selected lens prescription/focus state

Do not move the photocathode in software unless the physical C-mount/adaptor
geometry changes.

## Related Geant4 Resolution Target

Added 2026-06-20. Updated 2026-06-30.

The Siemens star resolution target is a Geant4-side scintillator-back-face mask.
It is not part of RayOptics. Its purpose is to generate a known spatial photon
pattern before optical transport.

Keep the first implementation simple:

- target type: Siemens star
- plane: scintillator `+Z` face
- material: existing absorbing mask material
- geometry: repeated `G4Tubs` annular sectors
- initial controls: enabled/disabled, outer radius, line-pair count

Useful pitch estimate:

```text
pitch_mm(r) = 2*pi*r_mm / linePairs
```

Keep this independent from the circular `maskRadius`; the circular mask controls
aperture or field, while the Siemens star provides a resolution pattern.

## TODO

Added 2026-06-30.

- Rewrite `src/optics/OpticalTransport.py` around the current Geant4 photon
  output path.
- Decide how lens mount/flange references map to the imported RayOptics/ZMX
  coordinate system for each catalog lens.
- Implement the focus-validation routine before bulk photon transport.
- Reconstruct object-plane rays from scintillator-exit and optical-interface
  records.
- Preserve photon provenance IDs in transported photon output.
- Mark trace failures, aperture misses, and active-area misses explicitly.
- Add a simple correct transport path first; add batching only after correctness
  is clear.
- Add focused tests for config validation, lens loading, focus validation, and
  photon provenance preservation.
