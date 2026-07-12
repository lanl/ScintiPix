# Autofocus

**Updated:** 2026-07-12  
**Status:** Autofocus implemented and tested; runner integration pending

## Purpose

Autofocus runs before Geant4. It traces synthetic rays through the selected
RayOptics lens prescription and updates the permitted physical degrees of
freedom needed to image the requested scintillator field of view (FOV) onto the
intensifier photocathode.

The requested FOV is a hard requirement. Autofocus does not silently crop or
replace it.

## Geometry

```text
scintillator back face -- working distance --> lens entrance / first surface
                                                -> modeled lens
                                                -> last optical surface
                                                   -- back focus --> photocathode
```

- The scintillator back face is the RayOptics object plane.
- The optical interface is the Geant4 scoring plane at the lens entrance.
- Working distance is measured from the scintillator back face to that lens
  entrance plane. It is not the interface's absolute `z` coordinate.
- Back focus is measured from the last modeled optical surface to the
  intensifier photocathode image plane.
- Internal focus adjustment moves only the gaps listed in `focusGaps`.

The working distance represented by a `Simulation` is:

```python
scintillator_back_z_mm = (
    scintillator.position_mm.z_mm + scintillator.dimension_mm.z_mm / 2
)
working_distance_mm = interface.position_mm.z_mm - scintillator_back_z_mm
```

## Mechanical Bounds

Autofocus searches only explicit bounds:

- `optical.interface.workingDistanceBoundsMm`
- `optical.lenses[*].focusAdjustmentBoundsMm`
- `optical.lenses[*].backFocusBoundsMm`

`workingDistanceBoundsMm` is required. Internal focus and back focus are varied
only when their bounds are provided. A `backFocusMm` without bounds is treated
as fixed geometry. Autofocus never invents a generic search range.

```yaml
optical:
  lenses:
    - catalogId: CanonEF50mmf1.0L
      primary: true
      focusAdjustmentBoundsMm: [-2.0, 2.0]  # Example only
      backFocusMm: 38.65                    # Example only
      backFocusBoundsMm: [30.0, 60.0]       # Example only
  interface:
    diameterMm: 60.55
    positionMm: {x_mm: 0.0, y_mm: 0.0, z_mm: 210.05}
    workingDistanceBoundsMm: [150.0, 1000.0]  # Example only
```

The numbers above demonstrate the schema. They are computational test bounds,
not validated Canon/adapter travel limits.

For C-mount, the flange focal distance is `17.526 mm` from the C-mount flange
shoulder to the image plane. It is not automatically the RayOptics back focus,
which begins at the last modeled optical surface. Real bounds must account for:

```text
last modeled surface -> native flange -> adapter -> C-mount flange -> photocathode
```

## Algorithm

1. Load the primary lens ZMX prescription.
2. Sample the FOV center, edge midpoints, and corners on the scintillator back
   face.
3. Trace inner and outer pupil rays through the sequential model with aperture
   checks enabled.
4. Compute RMS spot radius separately for every field point.
5. Minimize worst-field RMS spot size and image-circle fill error while
   penalizing rays outside the active intensifier radius.
6. Reject candidates that cannot trace enough rays, violate bounds, or fail to
   fit the requested FOV.
7. Update the validated `Simulation` directly:

   ```python
   config.optical.interface.position_mm.z_mm
   primary_lens.focus_adjustment_mm
   primary_lens.back_focus_mm
   ```

`auto_focus_lens(config)` returns `None`.

## Tested Prescriptions

The three catalog prescriptions pass the bounded integration test using a
100 x 100 mm FOV and an 18 mm intensifier image circle:

| Lens | Working distance | Focus adjustment | Back focus | Worst RMS spot |
|---|---:|---:|---:|---:|
| Canon EF 50 mm f/1.0L | 385.971 mm | +2.000 mm | 44.191 mm | 0.138857 mm |
| Nikkor 80-200 mm f/2.8D | 615.546 mm | +0.149 mm | 65.777 mm | 0.059734 mm |
| Nikkor Z 58 mm f/0.95 | 495.299 mm | -5.000 mm | 0.500 mm | 0.203119 mm |

These results validate the software path, not the mechanical assemblies. The
Canon and Nikkor Z solutions reached one or more computational test bounds.
Production configurations require measured or manufacturer-supported mount,
adapter, back-focus, and internal-focus limits.

The older statement that the Canon prescription cannot run at finite distance
is obsolete. Autofocus replaces its infinity object gap with a bounded finite
working distance before tracing.

## Current Status

Completed:

- bounded working-distance, internal-focus, and back-focus models
- finite-FOV sequential ray tracing
- active-area and aperture checks
- catalog loading for all three prescriptions
- three-lens bounded integration tests

Next:

- integrate the mutating `auto_focus_lens(config)` contract into
  `src/runner/runSimulation.py`
- replace computational bounds with validated mechanical bounds for production
  lens/adapter assemblies

## References

- Implementation: `src/optics/focus.py`
- Models: `src/models/optics.py`
- Tests: `test/unit/src/optics/test_focus.py`
- Lens catalog: `catalogs/lenses/catalog.yaml`
