"""Auto-focus lens optimization routines.

This module implements the auto-focus system that calculates optimal working
distance and internal lens focus adjustment (zfine) to properly image the
scintillator field of view onto the intensifier photocathode.

The optimization uses a hybrid two-stage approach:
1. Fast paraxial optimization to get in the ballpark
2. Rigorous ray-based refinement to account for real aberrations
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from loguru import logger
from scipy.optimize import minimize_scalar

if TYPE_CHECKING:
    from src.models.config import Simulation
    from src.models.optics import Lens

try:
    from rayoptics.optical.opticalmodel import OpticalModel
    from rayoptics.parax import firstorder
    from rayoptics.raytr import trace
    from rayoptics.seq.sequential import SequentialModel
    from rayoptics.zemax import zmxread
except ImportError as e:
    raise ImportError(
        "rayoptics is required for auto-focus functionality. "
        "Install it in your environment (e.g., pixi add ray-optics)."
    ) from e


C_MOUNT_FFD_MM = 17.526


def get_focus_gaps_as_tuples(lens: Lens) -> list[tuple[int, float, float]]:
    """Convert FocusGap objects to tuples for internal processing.

    Args:
        lens: Lens object with focus_gaps loaded from catalog

    Returns:
        List of (gap_index, default_thickness_mm, scaling_factor) tuples
    """
    if lens.focus_gaps is None:
        return []
    return [
        (gap.gap_index, gap.default_thickness_mm, gap.scaling_factor)
        for gap in lens.focus_gaps
    ]


def apply_focus_adjustment(
    seq_model: SequentialModel,
    focus_gaps: list[tuple[int, float, float]],
    zfine: float,
) -> None:
    """Apply zfine adjustment to internal lens gaps.

    Args:
        seq_model: rayOptics sequential model
        focus_gaps: List of (gap_index, default_thickness, scaling_factor) tuples
        zfine: Focus adjustment value in mm
    """
    for gap_idx, default_thi, scale in focus_gaps:
        seq_model.gaps[gap_idx].thi = default_thi + (zfine * scale)


def compute_image_distance_paraxial(opt_model: OpticalModel) -> float:
    """Calculate where image forms using first-order paraxial optics.

    This is fast but only uses paraxial approximation. Good for initial estimates.

    Args:
        opt_model: rayOptics OpticalModel

    Returns:
        Image distance from last surface in mm
    """
    seq_model = opt_model.seq_model
    stop = seq_model.stop_surface
    wvl = seq_model.central_wavelength()
    parax_data = firstorder.compute_first_order(opt_model, stop, wvl)
    return parax_data.fod.img_dist


def compute_spot_size_rms(
    opt_model: OpticalModel,
    field_positions: list[float] | None = None,
    num_rays: int = 10,
) -> float:
    """Trace real rays and measure RMS spot size at image plane.

    This is more rigorous than paraxial calculation because it:
    - Uses real ray tracing (not paraxial approximation)
    - Accounts for aberrations
    - Tests rays at different field positions and angles
    - Measures actual convergence quality

    Args:
        opt_model: rayOptics OpticalModel
        field_positions: List of normalized field positions [0.0, 0.7, 1.0]
        num_rays: Number of rays across pupil (grid will be num_rays x num_rays)

    Returns:
        RMS spot radius in mm at image plane
    """
    if field_positions is None:
        field_positions = [0.0, 0.7, 1.0]

    all_ray_coords = []

    for field_pos in field_positions:
        for px in np.linspace(-1, 1, num_rays):
            for py in np.linspace(-1, 1, num_rays):
                if px**2 + py**2 > 1.0:
                    continue

                try:
                    ray, _ray_op, _wvl = trace.trace_base(
                        opt_model,
                        pupil=[px, py],
                        fld=[field_pos, 0],
                    )

                    if ray is not None and len(ray) > 0:
                        x_img = ray[-1][0]
                        y_img = ray[-1][1]
                        all_ray_coords.append([x_img, y_img])

                except Exception:
                    continue

    if len(all_ray_coords) < 4:
        return float("inf")

    coords = np.array(all_ray_coords)
    centroid_x = np.mean(coords[:, 0])
    centroid_y = np.mean(coords[:, 1])

    distances = np.sqrt(
        (coords[:, 0] - centroid_x) ** 2 + (coords[:, 1] - centroid_y) ** 2
    )
    rms_radius = np.sqrt(np.mean(distances**2))

    return rms_radius


def compute_focus_error_at_fixed_plane(
    opt_model: OpticalModel,
    target_image_dist: float,
    field_positions: list[float] | None = None,
    num_rays: int = 10,
) -> float:
    """Measure how well rays converge at a fixed image distance.

    This is the most appropriate for C-mount constraint because:
    - The image plane position is FIXED (can't move)
    - We measure how well the lens focuses AT that plane
    - Smaller spot size = better focus

    Args:
        opt_model: rayOptics OpticalModel
        target_image_dist: Fixed image plane distance (17.526mm for C-mount)
        field_positions: Normalized field positions to test
        num_rays: Number of rays per dimension

    Returns:
        RMS spot size at the fixed image plane (mm)
    """
    seq_model = opt_model.seq_model

    seq_model.gaps[-1].thi = target_image_dist
    opt_model.update_model()

    return compute_spot_size_rms(opt_model, field_positions, num_rays)


def optimize_focus_hybrid(
    opt_model: OpticalModel,
    seq_model: SequentialModel,
    focus_gaps: list[tuple[int, float, float]],
    target_image_dist: float = C_MOUNT_FFD_MM,
    zfine_bounds: tuple[float, float] = (-20.0, 20.0),
) -> tuple[float, dict[str, float]]:
    """Find optimal focus using two-stage hybrid optimization.

    Stage 1: Fast paraxial optimization (ballpark)
    Stage 2: Rigorous ray-based refinement

    Args:
        opt_model: rayOptics OpticalModel
        seq_model: rayOptics SequentialModel
        focus_gaps: List of (gap_index, default_thickness, scaling_factor) tuples
        target_image_dist: Target image distance (C-mount FFD)
        zfine_bounds: Search bounds for zfine adjustment

    Returns:
        (optimal_zfine, metrics_dict)
    """

    def paraxial_error(zfine: float) -> float:
        apply_focus_adjustment(seq_model, focus_gaps, zfine)
        opt_model.update_model()
        actual_image_dist = compute_image_distance_paraxial(opt_model)
        return abs(actual_image_dist - target_image_dist)

    logger.debug("Stage 1: Coarse paraxial optimization...")
    result_coarse = minimize_scalar(
        paraxial_error,
        bounds=zfine_bounds,
        method="bounded",
    )

    zfine_coarse = result_coarse.x
    logger.debug(f"  Coarse zfine: {zfine_coarse:.3f} mm")
    logger.debug(f"  Image distance error: {result_coarse.fun:.6f} mm")

    def spot_size_error(zfine: float) -> float:
        apply_focus_adjustment(seq_model, focus_gaps, zfine)
        opt_model.update_model()
        return compute_focus_error_at_fixed_plane(
            opt_model,
            target_image_dist,
            field_positions=[0.0, 0.7, 1.0],
            num_rays=10,
        )

    logger.debug("Stage 2: Fine ray-based optimization...")
    narrow_bounds = (zfine_coarse - 2.0, zfine_coarse + 2.0)
    result_fine = minimize_scalar(
        spot_size_error,
        bounds=narrow_bounds,
        method="bounded",
        options={"xatol": 0.01},
    )

    optimal_zfine = result_fine.x
    final_spot_size = result_fine.fun

    logger.debug(f"  Optimal zfine: {optimal_zfine:.3f} mm")
    logger.debug(f"  RMS spot size: {final_spot_size:.6f} mm")
    logger.debug(f"  Adjustment from coarse: {optimal_zfine - zfine_coarse:.3f} mm")

    logger.debug("Validation with detailed rays...")
    apply_focus_adjustment(seq_model, focus_gaps, optimal_zfine)
    opt_model.update_model()
    spot_detailed = compute_focus_error_at_fixed_plane(
        opt_model,
        target_image_dist,
        field_positions=[0.0, 0.3, 0.5, 0.7, 0.85, 1.0],
        num_rays=20,
    )
    logger.debug(f"  Final RMS spot size: {spot_detailed:.6f} mm")

    metrics = {
        "zfine_coarse": zfine_coarse,
        "zfine_fine": optimal_zfine,
        "paraxial_error_mm": result_coarse.fun,
        "spot_size_mm": final_spot_size,
        "spot_size_detailed_mm": spot_detailed,
    }

    return optimal_zfine, metrics


def auto_focus_lens(config: Simulation) -> tuple[float, float]:
    """Calculate optimal working distance and focus adjustment.

    This function implements the complete auto-focus algorithm:
    1. Load lens prescription from ZMX file
    2. Load focus gaps from lens catalog
    3. Calculate magnification requirement from FOV and intensifier size
    4. Estimate working distance from magnification and lens focal length
    5. Optimize zfine to achieve focus at C-mount plane (iterative)
    6. Validate that FOV fits within intensifier active area
    7. Return optimal working distance and zfine

    Args:
        config: Simulation configuration

    Returns:
        (optimal_z_mm, focus_adjustment_mm)

    Raises:
        ValueError: If no primary lens found, no focus gaps defined, or FOV doesn't fit
        FileNotFoundError: If ZMX file not found
    """
    primary_lens = next(
        (lens for lens in config.optical.lenses if lens.primary), None
    )
    if primary_lens is None:
        raise ValueError("No primary lens found in configuration")

    if primary_lens.zmx_file is None:
        raise ValueError(f"Primary lens '{primary_lens.name}' has no zmx_file defined")

    zmx_path = Path(primary_lens.zmx_file)
    if not zmx_path.exists():
        raise FileNotFoundError(f"ZMX file not found: {zmx_path}")

    focus_gaps = get_focus_gaps_as_tuples(primary_lens)
    if not focus_gaps:
        raise ValueError(
            f"Primary lens '{primary_lens.name}' has no focus_gaps defined. "
            "Auto-focus requires focus gap definitions in the lens catalog."
        )

    scintillator_fov = config.scintillator.field_of_view
    fov_width_mm = scintillator_fov.width_mm
    fov_height_mm = scintillator_fov.height_mm
    fov_diagonal_mm = np.sqrt(fov_width_mm**2 + fov_height_mm**2)

    intensifier_diameter_mm = (
        config.intensifier.input_screen.image_circle_diameter_mm
    )

    required_magnification = intensifier_diameter_mm / fov_diagonal_mm

    logger.info("Auto-focus calculation:")
    logger.info(f"  Scintillator FOV: {fov_width_mm:.2f} x {fov_height_mm:.2f} mm")
    logger.info(f"  FOV diagonal: {fov_diagonal_mm:.2f} mm")
    logger.info(f"  Intensifier diameter: {intensifier_diameter_mm:.2f} mm")
    logger.info(f"  Required magnification: {required_magnification:.4f}")

    if required_magnification > 1.0:
        logger.warning(
            f"Required magnification {required_magnification:.4f} > 1.0. "
            "This may require additional optical elements or a smaller FOV."
        )

    logger.debug(f"Loading lens model from: {zmx_path}")
    opt_model = zmxread.read_lens_file(zmx_path, info=False)
    if isinstance(opt_model, tuple):
        opt_model = opt_model[0]

    seq_model = opt_model.seq_model

    stop = seq_model.stop_surface
    wvl = seq_model.central_wavelength()
    parax_data = firstorder.compute_first_order(opt_model, stop, wvl)
    effective_focal_length = parax_data.fod.efl

    logger.debug(f"Lens effective focal length: {effective_focal_length:.3f} mm")

    working_distance_estimate = effective_focal_length * (1.0 + 1.0 / required_magnification)

    initial_guess_z = config.optical.interface.position_mm.z_mm
    if abs(initial_guess_z - working_distance_estimate) > 20.0:
        logger.info(
            f"Initial working distance guess ({initial_guess_z:.2f} mm) differs "
            f"from thin-lens estimate ({working_distance_estimate:.2f} mm). "
            f"Using estimate as starting point."
        )
        working_distance_mm = working_distance_estimate
    else:
        working_distance_mm = initial_guess_z

    logger.info(f"  Working distance: {working_distance_mm:.2f} mm")

    seq_model.gaps[0].thi = working_distance_mm
    opt_model.update_model()

    logger.info("Optimizing internal focus adjustment...")
    optimal_zfine, metrics = optimize_focus_hybrid(
        opt_model, seq_model, focus_gaps, target_image_dist=C_MOUNT_FFD_MM
    )

    logger.info(f"  Optimal focus adjustment (zfine): {optimal_zfine:.3f} mm")
    logger.info(f"  Final RMS spot size: {metrics['spot_size_detailed_mm']:.6f} mm")

    if metrics["spot_size_detailed_mm"] > 0.1:
        logger.warning(
            f"Large RMS spot size ({metrics['spot_size_detailed_mm']:.3f} mm) "
            "indicates poor focus quality. Check lens prescription and focus gaps."
        )

    actual_magnification = abs(
        intensifier_diameter_mm / (seq_model.gaps[0].thi * required_magnification)
    )

    image_width_mm = fov_width_mm * actual_magnification
    image_height_mm = fov_height_mm * actual_magnification
    image_diagonal_mm = np.sqrt(image_width_mm**2 + image_height_mm**2)

    logger.info(f"  Image size on intensifier: {image_width_mm:.2f} x {image_height_mm:.2f} mm")
    logger.info(f"  Image diagonal: {image_diagonal_mm:.2f} mm")

    if image_diagonal_mm > intensifier_diameter_mm:
        raise ValueError(
            f"Scintillator FOV ({fov_diagonal_mm:.2f} mm) does not fit within "
            f"intensifier active area ({intensifier_diameter_mm:.2f} mm). "
            f"Image diagonal ({image_diagonal_mm:.2f} mm) exceeds intensifier diameter. "
            "Reduce scintillator FOV or use a different lens."
        )

    fill_factor = image_diagonal_mm / intensifier_diameter_mm
    logger.info(f"  Intensifier fill factor: {fill_factor:.1%}")

    if fill_factor < 0.5:
        logger.warning(
            f"Low fill factor ({fill_factor:.1%}) - consider increasing FOV "
            "or using a different lens to better utilize the intensifier area."
        )

    logger.success("Auto-focus optimization complete")

    return working_distance_mm, optimal_zfine
