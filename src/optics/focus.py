"""Bounded pre-Geant4 autofocus using RayOptics."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from loguru import logger
from scipy.optimize import minimize

from rayoptics.raytr import trace
from rayoptics.raytr.traceerror import TraceError
from rayoptics.zemax import zmxread

if TYPE_CHECKING:
    from rayoptics.optical.opticalmodel import OpticalModel
    from src.models.optics import Lens
    from src.models.simulation import Simulation


_PUPIL_POINTS = (
    (0.0, 0.0),
    (-0.7, 0.0),
    (0.7, 0.0),
    (0.0, -0.7),
    (0.0, 0.7),
    (-0.5, -0.5),
    (-0.5, 0.5),
    (0.5, -0.5),
    (0.5, 0.5),
)


def _primary_lens(config: Simulation) -> Lens:
    if config.optical is None or not config.optical.lenses:
        raise ValueError("Autofocus requires an optical lens configuration.")

    return next(lens for lens in config.optical.lenses if lens.primary)


def _object_field_points(
    width_mm: float,
    height_mm: float,
) -> tuple[tuple[float, float], ...]:
    """Return FOV center, edge, and corner object points."""

    half_width = width_mm / 2.0
    half_height = height_mm / 2.0
    return (
        (0.0, 0.0),
        (-half_width, 0.0),
        (half_width, 0.0),
        (0.0, -half_height),
        (0.0, half_height),
        (-half_width, -half_height),
        (-half_width, half_height),
        (half_width, -half_height),
        (half_width, half_height),
    )


def _apply_geometry(
    opt_model: OpticalModel,
    lens: Lens,
    working_distance_mm: float,
    focus_adjustment_mm: float,
    back_focus_mm: float,
) -> None:
    """Apply one mechanically valid candidate to the sequential model."""

    seq_model = opt_model["seq_model"]
    seq_model.gaps[0].thi = working_distance_mm
    seq_model.gaps[-1].thi = back_focus_mm

    for focus_gap in lens.focus_gaps or []:
        if not 0 < focus_gap.gap_index < len(seq_model.gaps) - 1:
            raise ValueError(
                f"Focus gap index {focus_gap.gap_index} is not an internal lens gap."
            )
        thickness_mm = (
            focus_gap.default_thickness_mm
            + focus_adjustment_mm * focus_gap.scaling_factor
        )
        if thickness_mm <= 0.0:
            raise ValueError(
                f"Focus adjustment makes gap {focus_gap.gap_index} non-positive."
            )
        seq_model.gaps[focus_gap.gap_index].thi = thickness_mm

    seq_model.update_model()


def _trace_fov(
    opt_model: OpticalModel,
    field_points: tuple[tuple[float, float], ...],
    entrance_radius_mm: float,
) -> tuple[float, float, float] | None:
    """Return worst RMS spot, outer centroid radius, and outer ray radius."""

    wavelength_nm = opt_model["seq_model"].central_wavelength()
    seq_model = opt_model["seq_model"]
    rms_spots: list[float] = []
    centroid_radii: list[float] = []
    ray_radii: list[float] = []

    working_distance_mm = seq_model.gaps[0].thi
    for field_x_mm, field_y_mm in field_points:
        image_points: list[np.ndarray] = []
        for pupil in _PUPIL_POINTS:
            object_point = np.asarray([field_x_mm, field_y_mm, 0.0])
            entrance_point = np.asarray(
                [
                    pupil[0] * entrance_radius_mm,
                    pupil[1] * entrance_radius_mm,
                    working_distance_mm,
                ]
            )
            direction = entrance_point - object_point
            direction /= np.linalg.norm(direction)
            try:
                ray_package = trace.trace(
                    seq_model,
                    object_point,
                    direction,
                    wavelength_nm,
                    check_apertures=True,
                )
            except TraceError:
                continue
            image_points.append(np.asarray(ray_package.ray[-1][0][:2]))

        if len(image_points) < 4:
            return None

        points = np.asarray(image_points)
        centroid = points.mean(axis=0)
        rms_spots.append(
            float(np.sqrt(np.mean(np.sum((points - centroid) ** 2, axis=1))))
        )
        centroid_radii.append(float(np.linalg.norm(centroid)))
        ray_radii.extend(float(np.linalg.norm(point)) for point in points)

    return max(rms_spots), max(centroid_radii), max(ray_radii)


def auto_focus_lens(config: Simulation) -> None:
    """Optimize the configured lens within explicit mechanical bounds.

    The requested scintillator FOV is fixed. The routine updates the optical
    interface position and the primary lens focus state in ``config``.
    """

    if config.optical is None:
        raise ValueError("Autofocus requires `optical` configuration.")
    if config.intensifier is None:
        raise ValueError("Autofocus requires `intensifier` configuration.")

    lens = _primary_lens(config)
    interface = config.optical.interface
    fov = config.scintillator.field_of_view
    if fov is None:
        raise ValueError("Autofocus requires a scintillator field of view.")
    if interface.working_distance_bounds_mm is None:
        raise ValueError(
            "Autofocus requires `optical.interface.workingDistanceBoundsMm`."
        )
    if lens.back_focus_mm is None and lens.back_focus_bounds_mm is None:
        raise ValueError(
            "Autofocus requires `backFocusMm` or `backFocusBoundsMm` on the primary lens."
        )
    if lens.focus_adjustment_bounds_mm is not None and not lens.focus_gaps:
        raise ValueError(
            "`focusAdjustmentBoundsMm` requires configured `focusGaps`."
        )
    if lens.zmx_file is None:
        raise ValueError(f"Primary lens '{lens.name}' has no ZMX prescription.")

    zmx_path = Path(lens.zmx_file)
    if not zmx_path.exists():
        raise FileNotFoundError(f"ZMX prescription not found: {zmx_path}")

    scintillator_back_z_mm = (
        config.scintillator.position_mm.z_mm
        + config.scintillator.dimension_mm.z_mm / 2.0
    )
    working_distance_mm = interface.position_mm.z_mm - scintillator_back_z_mm
    working_bounds = interface.working_distance_bounds_mm
    if not working_bounds[0] <= working_distance_mm <= working_bounds[1]:
        raise ValueError(
            "Configured working distance lies outside `workingDistanceBoundsMm`."
        )

    opt_model, _import_info = zmxread.read_lens_file(zmx_path, info=False)
    field_points = _object_field_points(fov.width_mm, fov.height_mm)
    entrance_radius_mm = interface.diameter_mm / 2.0

    variable_names = ["working_distance_mm"]
    initial_values = [working_distance_mm]
    bounds = [working_bounds]

    fixed_focus_mm = lens.focus_adjustment_mm or 0.0
    if lens.focus_adjustment_bounds_mm is not None:
        focus_bounds = lens.focus_adjustment_bounds_mm
        fixed_focus_mm = min(max(fixed_focus_mm, focus_bounds[0]), focus_bounds[1])
        variable_names.append("focus_adjustment_mm")
        initial_values.append(fixed_focus_mm)
        bounds.append(focus_bounds)

    if lens.back_focus_bounds_mm is not None:
        back_focus_bounds = lens.back_focus_bounds_mm
        initial_back_focus_mm = lens.back_focus_mm
        if initial_back_focus_mm is None:
            initial_back_focus_mm = sum(back_focus_bounds) / 2.0
        variable_names.append("back_focus_mm")
        initial_values.append(initial_back_focus_mm)
        bounds.append(back_focus_bounds)
        fixed_back_focus_mm = initial_back_focus_mm
    else:
        fixed_back_focus_mm = lens.back_focus_mm

    assert fixed_back_focus_mm is not None
    image_radius_mm = config.intensifier.input_screen.image_circle_diameter_mm / 2.0

    def candidate_state(values: np.ndarray) -> dict[str, float]:
        state = {
            "working_distance_mm": working_distance_mm,
            "focus_adjustment_mm": fixed_focus_mm,
            "back_focus_mm": fixed_back_focus_mm,
        }
        state.update(zip(variable_names, values, strict=True))
        return state

    def objective(values: np.ndarray) -> float:
        state = candidate_state(values)
        try:
            _apply_geometry(opt_model, lens, **state)
            metrics = _trace_fov(opt_model, field_points, entrance_radius_mm)
        except Exception as exc:
            logger.debug(f"Rejected autofocus candidate: {exc}")
            return 1.0e9

        if metrics is None:
            return 1.0e9

        worst_rms_mm, outer_centroid_mm, outer_ray_mm = metrics
        fill_error_mm = abs(outer_centroid_mm - image_radius_mm)
        active_area_penalty = 100.0 * max(0.0, outer_ray_mm - image_radius_mm)
        return worst_rms_mm + fill_error_mm + active_area_penalty

    logger.info(
        f"Autofocus: optimizing {', '.join(variable_names)} for lens '{lens.name}'"
    )
    result = minimize(
        objective,
        np.asarray(initial_values),
        method="Powell",
        bounds=bounds,
        options={"xtol": 1.0e-3, "ftol": 1.0e-6, "maxiter": 100},
    )
    if not np.isfinite(result.fun) or result.fun >= 1.0e8:
        raise ValueError(
            "Autofocus could not trace a valid solution within the mechanical bounds."
        )

    solution = candidate_state(result.x)
    _apply_geometry(opt_model, lens, **solution)
    metrics = _trace_fov(opt_model, field_points, entrance_radius_mm)
    if metrics is None:
        raise ValueError("Autofocus solution did not produce enough valid rays.")

    worst_rms_mm, outer_centroid_mm, outer_ray_mm = metrics
    if outer_ray_mm > image_radius_mm + 1.0e-3:
        raise ValueError(
            "The requested scintillator FOV does not fit on the intensifier "
            "within the configured mechanical bounds."
        )

    interface.position_mm.z_mm = (
        scintillator_back_z_mm + solution["working_distance_mm"]
    )
    lens.focus_adjustment_mm = solution["focus_adjustment_mm"]
    lens.back_focus_mm = solution["back_focus_mm"]

    logger.success(
        "Autofocus complete: "
        f"working distance={solution['working_distance_mm']:.3f} mm, "
        f"focus adjustment={solution['focus_adjustment_mm']:.3f} mm, "
        f"back focus={solution['back_focus_mm']:.3f} mm, "
        f"worst RMS spot={worst_rms_mm:.6f} mm, "
        f"image radius={outer_centroid_mm:.3f} mm"
    )
