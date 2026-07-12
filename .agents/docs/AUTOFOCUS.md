# Auto-Focus Implementation

**Updated:** 2026-07-12  
**Status:** In Progress

---

## Overview

Auto-focus runs before Geant4 and adjusts the permitted physical degrees of
freedom so the selected lens images the requested scintillator field of view
(FOV) onto the intensifier photocathode.

**Key Requirements:**
1. Treat the requested scintillator FOV as a hard coverage requirement.
2. Keep the intensifier photocathode as the RayOptics image plane.
3. Search only mechanically attainable working distances, internal lens gaps,
   and back-focus distances.
4. Minimize RMS spot size across representative FOV points.

---

## Geometry Definitions

```text
scintillator back face -- working distance --> lens entrance / first surface
                                                -> modeled lens
                                                -> last optical surface
                                                   -- back focus --> photocathode
```

- **Scintillator back face:** RayOptics object plane.
- **Optical interface:** Geant4 scoring plane representing the lens entrance
  plane. It is not the RayOptics object or image plane.
- **Working distance:** Distance from the scintillator back face to the lens
  entrance plane. It is not the absolute interface `z` coordinate.
- **Back focus:** Distance from the last modeled optical surface to the
  intensifier photocathode image plane.
- **Focus adjustment:** Motion of the internal lens gaps listed in
  `focusGaps`.

For a scintillator centered at `position_mm.z_mm`, the current geometry uses:

```python
scintillator_back_z_mm = (
    scintillator.position_mm.z_mm + scintillator.dimension_mm.z_mm / 2
)
working_distance_mm = interface.position_mm.z_mm - scintillator_back_z_mm
```

## Mechanical Back-Focus Constraint

`backFocusMm` records the current or fixed distance from the prescription's
last modeled optical surface to the photocathode. `backFocusBoundsMm` records
the physically attainable interval for an adjustable assembly.

```yaml
optical:
  lenses:
    - catalogId: CanonEF50mmf1.0L
      primary: true
      backFocusMm: 24.3
      backFocusBoundsMm: [23.8, 24.8]
```

The bounds must account for the complete mechanical stack:

```text
last modeled optical surface
    -> native lens flange
    -> adapter
    -> C-mount flange
    -> intensifier photocathode
```

The C-mount flange focal distance is `17.526 mm`, measured from the C-mount
flange shoulder to the image plane. It is not automatically the RayOptics final
image gap, which begins at the last modeled optical surface.

Autofocus follows these rules:

- `backFocusMm` without bounds is fixed geometry.
- `backFocusBoundsMm` permits optimization only within those bounds.
- Bounds without an initial value use their midpoint as the initial value.
- Missing back-focus geometry is an error when autofocus needs it.
- Autofocus never invents a generic back-focus search range.

## Planned Algorithm

### 1. Calculate Required Magnification

```python
M = intensifier_diameter / scintillator_fov_diagonal
```

### 2. Estimate Working Distance

```python
working_distance = focal_length * (1 + 1/M)  # Thin lens approximation
```

This estimate initializes the search; it is not the final optical result.

### 3. Optimize Permitted Degrees of Freedom

- Vary working distance within its allowed geometry.
- Vary configured internal focus gaps within their allowed travel.
- Vary back focus only when `backFocusBoundsMm` is present.
- Trace each field point separately.
- Minimize the summarized per-field RMS spot size at the photocathode.
- Reject solutions that do not cover the requested FOV or violate mechanical
  bounds.

### 4. Update the Simulation

The routine updates the validated `Simulation` before Geant4 macro generation:

```python
config.optical.interface.position_mm.z_mm
primary_lens.focus_adjustment_mm
primary_lens.back_focus_mm
```

The requested scintillator FOV is not changed by autofocus.

---

## Implementation Status

**Completed:**
- ✅ Models (`FocusGap`, lens catalog structure)
- ✅ Back-focus value and mechanical bounds on `Lens`
- ✅ Focus gaps identified (Canon: gap 10, Nikkor: gaps 22/24/31)

**In Progress:**
- Rewrite `src/optics/focus.py` around the geometry contract above.
- Define mechanically valid working-distance and internal-gap search bounds.
- Update the runner so autofocus updates the validated `Simulation` directly.
- Add focused model and ray-tracing tests.

**Known Lens Issues:**
- Canon EF 50mm ZMX fails at finite distances (DISZ INFINITY)
- Nikkor Z 58mm ZMX works but needs G4LumaCam modifications (gap 22: 21.29mm → 2.68mm)
- Need proper lens for Navitar DO-5095 proxy

---

## Lens Catalog

Focus gaps defined in `catalogs/lenses/catalog.yaml`:

```yaml
CanonEF50mmf1.0L:
  focusGaps:
    - gapIndex: 10
      defaultThickness: 10.229
      scalingFactor: 1.0

NikkorZ58mmf0.95:
  focusGaps:
    - gapIndex: 22
      defaultThickness: 21.29  # G4LumaCam uses 2.68mm
      scalingFactor: 1.0
```

---

## References

- Implementation: `src/optics/focus.py`
- G4LumaCam: https://github.com/TsvikiHirsh/G4LumaCam
- C-mount flange focal distance: 17.526 mm
