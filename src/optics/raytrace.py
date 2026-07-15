"""Transport simulated photons through a focused RayOptics lens model."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from loguru import logger
from rayoptics.raytr import trace
from rayoptics.raytr.traceerror import TraceError
from rayoptics.zemax import zmxread

from src.optics.focus import _apply_geometry, _primary_lens
from src.optics.io import (
    TRANSPORTED_PHOTON_DTYPE,
    read_simulated_photons,
    write_transported_photons,
)

if TYPE_CHECKING:
    from rayoptics.optical.opticalmodel import OpticalModel
    from src.models.simulation import Simulation


_SPEED_OF_LIGHT_MM_PER_NS = 299.792458


def load_lens_model(config: Simulation) -> OpticalModel:
    """Load the primary lens and apply geometry stored on ``config``."""

    if config.optical is None:
        raise ValueError("Optical transport requires `optical` configuration.")
    if config.intensifier is None:
        raise ValueError("Optical transport requires `intensifier` configuration.")

    lens = _primary_lens(config)
    if lens.zmx_file is None:
        raise ValueError(f"Primary lens '{lens.name}' has no ZMX prescription.")
    if lens.back_focus_mm is None:
        raise ValueError(
            "Optical transport requires the focused primary lens `backFocusMm`."
        )

    zmx_path = Path(lens.zmx_file)
    if not zmx_path.is_file():
        raise FileNotFoundError(f"ZMX prescription not found: {zmx_path}")
    if lens.smx_file is not None and not Path(lens.smx_file).is_file():
        raise FileNotFoundError(f"SMX glass substitutions not found: {lens.smx_file}")

    scintillator_back_z_mm = (
        config.scintillator.position_mm.z_mm
        + config.scintillator.dimension_mm.z_mm / 2.0
    )
    working_distance_mm = (
        config.optical.interface.position_mm.z_mm - scintillator_back_z_mm
    )
    if working_distance_mm <= 0.0:
        raise ValueError("Optical transport requires a positive working distance.")

    opt_model, _import_info = zmxread.read_lens_file(zmx_path, info=False)
    _apply_geometry(
        opt_model,
        lens,
        working_distance_mm=working_distance_mm,
        focus_adjustment_mm=lens.focus_adjustment_mm or 0.0,
        back_focus_mm=lens.back_focus_mm,
    )
    return opt_model


def trace_photons(
    config: Simulation,
    opt_model: OpticalModel,
    photons: np.ndarray,
    *,
    source_index_start: int = 0,
) -> np.ndarray:
    """Trace photons and return only hits inside the photocathode image plane."""

    if config.optical is None or config.intensifier is None:
        raise ValueError(
            "Optical transport requires `optical` and `intensifier` configuration."
        )

    seq_model = opt_model["seq_model"]
    working_distance_mm = float(seq_model.gaps[0].thi)
    supported_wavelengths_nm = tuple(float(value) for value in seq_model.wvlns)
    if not supported_wavelengths_nm:
        raise ValueError("The RayOptics lens model has no trace wavelengths.")
    center_x_mm, center_y_mm = config.intensifier.input_screen.center_mm
    image_radius_mm = (
        config.intensifier.input_screen.image_circle_diameter_mm / 2.0
    )
    transported: list[tuple[object, ...]] = []

    for source_index, photon in enumerate(photons, start=source_index_start):
        point = np.asarray(
            [
                photon["photon_scint_exit_x_mm"],
                photon["photon_scint_exit_y_mm"],
                0.0,
            ],
            dtype=float,
        )
        direction = np.asarray(
            [
                photon["optical_interface_hit_dir_x"],
                photon["optical_interface_hit_dir_y"],
                photon["optical_interface_hit_dir_z"],
            ],
            dtype=float,
        )
        wavelength_nm = float(photon["optical_interface_hit_wavelength_nm"])
        direction_norm = np.linalg.norm(direction)
        if (
            not np.all(np.isfinite(point))
            or not np.all(np.isfinite(direction))
            or not np.isfinite(wavelength_nm)
            or wavelength_nm <= 0.0
            or direction_norm == 0.0
        ):
            continue

        try:
            trace_wavelength_nm = min(
                supported_wavelengths_nm,
                key=lambda supported: abs(supported - wavelength_nm),
            )
            ray_package = trace.trace(
                seq_model,
                point,
                direction / direction_norm,
                trace_wavelength_nm,
                check_apertures=True,
            )
        except TraceError:
            continue

        image_point = np.asarray(ray_package.ray[-1][0], dtype=float)
        if image_point.size < 3 or not np.all(np.isfinite(image_point[:3])):
            continue
        if (
            (image_point[0] - center_x_mm) ** 2
            + (image_point[1] - center_y_mm) ** 2
            > image_radius_mm**2
        ):
            continue

        lens_path_mm = max(0.0, float(ray_package.op) - working_distance_mm)
        image_time_ns = (
            float(photon["optical_interface_hit_time_ns"])
            + lens_path_mm / _SPEED_OF_LIGHT_MM_PER_NS
        )
        transported.append(
            (
                source_index,
                photon["gun_call_id"],
                photon["primary_track_id"],
                photon["secondary_track_id"],
                photon["photon_track_id"],
                bytes(4),
                image_point[0],
                image_point[1],
                image_point[2],
                image_time_ns,
                wavelength_nm,
            )
        )

    return np.asarray(transported, dtype=TRANSPORTED_PHOTON_DTYPE)


def transport_photons(config: Simulation) -> Path:
    """Read, trace, and write photons using paths from ``config``."""

    environment = config.metadata.run_environment
    if environment.simulated_photons_directory is None:
        raise ValueError("Simulated photons directory is not configured.")
    if environment.transported_photons_directory is None:
        raise ValueError("Transported photons directory is not configured.")

    input_path = (
        Path(environment.simulated_photons_directory) / environment.photons_filename
    )
    output_path = (
        Path(environment.transported_photons_directory) / environment.photons_filename
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    photons = read_simulated_photons(input_path)
    logger.info(f"[optics] Tracing {len(photons)} simulated photons.")

    opt_model = load_lens_model(config)
    transported = trace_photons(config, opt_model, photons)
    write_transported_photons(output_path, transported)
    logger.success(
        f"[optics] Wrote {len(transported)} photocathode hits to {output_path}."
    )
    return output_path
