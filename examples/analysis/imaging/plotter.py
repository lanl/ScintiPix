"""Plot 2D images"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes

# Import from src/optics/io.py
try:
    from src.optics.io import read_transported_photons, read_simulated_photons
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.optics.io import read_transported_photons, read_simulated_photons


def image_transported_photons(
    transported_photons_bin: str | Path,
    *,
    bins: int = 100,
    extent_mm: float | None = None,
    cmap: str = "hot",
    output_path: str | Path | None = None,
    show: bool = True,
    title: str | None = None,
    log_scale: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """Create 2D histogram image of photocathode hits.

    Args:
        transported_photons_bin: Path to transportedPhotons/photons.bin file
        bins: Number of bins per axis for the 2D histogram (default: 100)
        extent_mm: Symmetric extent in mm (e.g., 10 for [-10, 10] range).
                   If None, uses data extent with 5% padding.
        cmap: Matplotlib colormap name (default: "hot")
        output_path: If provided, save figure to this path
        show: If True, display the plot (default: True)
        title: Custom title for the plot. If None, auto-generates from data.
        log_scale: If True, use log scale for color mapping (default: False)

    Returns:
        (fig, ax): Matplotlib figure and axes objects

    Example:
        >>> from analysis.imaging.plotter import image_transported_photons
        >>> fig, ax = image_transported_photons(
        ...     "data/run_000/transportedPhotons/photons.bin",
        ...     bins=200,
        ...     extent_mm=10,
        ...     output_path="photocathode_image.png"
        ... )
    """
    # Read transported photons (returns numpy structured array)
    photons = read_transported_photons(transported_photons_bin)

    if len(photons) == 0:
        raise ValueError("No transported photons found in file")

    x = photons["photocathode_hit_x_mm"]
    y = photons["photocathode_hit_y_mm"]

    # Determine extent
    if extent_mm is not None:
        extent = (-extent_mm, extent_mm, -extent_mm, extent_mm)
        range_xy = [[-extent_mm, extent_mm], [-extent_mm, extent_mm]]
    else:
        # Use data extent with 5% padding
        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()
        x_pad = (x_max - x_min) * 0.05
        y_pad = (y_max - y_min) * 0.05
        extent = (x_min - x_pad, x_max + x_pad, y_min - y_pad, y_max + y_pad)
        range_xy = [[extent[0], extent[1]], [extent[2], extent[3]]]

    # Create 2D histogram
    fig, ax = plt.subplots(figsize=(10, 10))

    # Compute histogram
    hist, xedges, yedges = np.histogram2d(x, y, bins=bins, range=range_xy)

    # Apply log scale if requested
    if log_scale:
        hist = np.log10(hist + 1)  # +1 to avoid log(0)
        label = "log10(Photon count + 1)"
    else:
        label = "Photon count"

    # Plot
    im = ax.imshow(
        hist.T,
        origin="lower",
        extent=extent,
        cmap=cmap,
        aspect="equal",
        interpolation="nearest",
    )

    # Colorbar
    plt.colorbar(im, ax=ax, label=label)

    # Labels and title
    ax.set_xlabel("X (mm)", fontsize=12)
    ax.set_ylabel("Y (mm)", fontsize=12)

    if title is None:
        title = f"Photocathode Image ({len(photons):,} photons)"
    ax.set_title(title, fontsize=14)

    # Add grid
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

    # Equal aspect ratio
    ax.set_aspect("equal")

    # Tight layout
    fig.tight_layout()

    # Save if requested
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved image to: {output_path}")

    # Show if requested
    if show:
        plt.show()

    return fig, ax


def image_scintillator_photons(
    simulated_photons_bin: str | Path,
    *,
    bins: int = 100,
    extent_mm: float | None = None,
    cmap: str = "hot",
    output_path: str | Path | None = None,
    show: bool = True,
    title: str | None = None,
    log_scale: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """Create 2D histogram image of scintillator photon hits at optical interface.

    Args:
        simulated_photons_bin: Path to simulatedPhotons/photons.bin file
        bins: Number of bins per axis for the 2D histogram (default: 100)
        extent_mm: Symmetric extent in mm (e.g., 20 for [-20, 20] range).
                   If None, uses data extent with 5% padding.
        cmap: Matplotlib colormap name (default: "hot")
        output_path: If provided, save figure to this path
        show: If True, display the plot (default: True)
        title: Custom title for the plot. If None, auto-generates from data.
        log_scale: If True, use log scale for color mapping (default: False)

    Returns:
        (fig, ax): Matplotlib figure and axes objects

    Example:
        >>> from analysis.imaging.plotter import image_scintillator_photons
        >>> fig, ax = image_scintillator_photons(
        ...     "data/run_000/simulatedPhotons/photons.bin",
        ...     bins=200,
        ...     extent_mm=20,
        ...     output_path="scintillator_image.png"
        ... )
    """
    # Read simulated photons (returns numpy structured array)
    photons = read_simulated_photons(simulated_photons_bin)

    if len(photons) == 0:
        raise ValueError("No simulated photons found in file")

    x = photons["optical_interface_hit_x_mm"]
    y = photons["optical_interface_hit_y_mm"]

    # Determine extent
    if extent_mm is not None:
        extent = (-extent_mm, extent_mm, -extent_mm, extent_mm)
        range_xy = [[-extent_mm, extent_mm], [-extent_mm, extent_mm]]
    else:
        # Use data extent with 5% padding
        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()
        x_pad = (x_max - x_min) * 0.05
        y_pad = (y_max - y_min) * 0.05
        extent = (x_min - x_pad, x_max + x_pad, y_min - y_pad, y_max + y_pad)
        range_xy = [[extent[0], extent[1]], [extent[2], extent[3]]]

    # Create 2D histogram
    fig, ax = plt.subplots(figsize=(10, 10))

    # Compute histogram
    hist, xedges, yedges = np.histogram2d(x, y, bins=bins, range=range_xy)

    # Apply log scale if requested
    if log_scale:
        hist = np.log10(hist + 1)  # +1 to avoid log(0)
        label = "log10(Photon count + 1)"
    else:
        label = "Photon count"

    # Plot
    im = ax.imshow(
        hist.T,
        origin="lower",
        extent=extent,
        cmap=cmap,
        aspect="equal",
        interpolation="nearest",
    )

    # Colorbar
    plt.colorbar(im, ax=ax, label=label)

    # Labels and title
    ax.set_xlabel("X (mm)", fontsize=12)
    ax.set_ylabel("Y (mm)", fontsize=12)

    if title is None:
        title = f"Optical Interface ({len(photons):,} photons)"
    ax.set_title(title, fontsize=14)

    # Add grid
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

    # Equal aspect ratio
    ax.set_aspect("equal")

    # Tight layout
    fig.tight_layout()

    # Save if requested
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved image to: {output_path}")

    # Show if requested
    if show:
        plt.show()

    return fig, ax


def image_scintillator_exit(
    simulated_photons_bin: str | Path,
    *,
    bins: int = 100,
    extent_mm: float | None = None,
    cmap: str = "hot",
    output_path: str | Path | None = None,
    show: bool = True,
    title: str | None = None,
    log_scale: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """Create 2D histogram image of photon positions at scintillator exit.

    This shows the pattern RIGHT at the scintillator back face where the
    Siemens star is located, before photons propagate to the optical interface.

    Args:
        simulated_photons_bin: Path to simulatedPhotons/photons.bin file
        bins: Number of bins per axis for the 2D histogram (default: 100)
        extent_mm: Symmetric extent in mm (e.g., 20 for [-20, 20] range).
                   If None, uses data extent with 5% padding.
        cmap: Matplotlib colormap name (default: "hot")
        output_path: If provided, save figure to this path
        show: If True, display the plot (default: True)
        title: Custom title for the plot. If None, auto-generates from data.
        log_scale: If True, use log scale for color mapping (default: False)

    Returns:
        (fig, ax): Matplotlib figure and axes objects

    Example:
        >>> from analysis.imaging.plotter import image_scintillator_exit
        >>> fig, ax = image_scintillator_exit(
        ...     "data/run_000/simulatedPhotons/photons.bin",
        ...     bins=200,
        ...     extent_mm=20,
        ...     output_path="scintillator_exit.png"
        ... )
    """
    # Read simulated photons (returns numpy structured array)
    photons = read_simulated_photons(simulated_photons_bin)

    if len(photons) == 0:
        raise ValueError("No simulated photons found in file")

    x = photons["photon_scint_exit_x_mm"]
    y = photons["photon_scint_exit_y_mm"]

    # Determine extent
    if extent_mm is not None:
        extent = (-extent_mm, extent_mm, -extent_mm, extent_mm)
        range_xy = [[-extent_mm, extent_mm], [-extent_mm, extent_mm]]
    else:
        # Use data extent with 5% padding
        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()
        x_pad = (x_max - x_min) * 0.05
        y_pad = (y_max - y_min) * 0.05
        extent = (x_min - x_pad, x_max + x_pad, y_min - y_pad, y_max + y_pad)
        range_xy = [[extent[0], extent[1]], [extent[2], extent[3]]]

    # Create 2D histogram
    fig, ax = plt.subplots(figsize=(10, 10))

    # Compute histogram
    hist, xedges, yedges = np.histogram2d(x, y, bins=bins, range=range_xy)

    # Apply log scale if requested
    if log_scale:
        hist = np.log10(hist + 1)  # +1 to avoid log(0)
        label = "log10(Photon count + 1)"
    else:
        label = "Photon count"

    # Plot
    im = ax.imshow(
        hist.T,
        origin="lower",
        extent=extent,
        cmap=cmap,
        aspect="equal",
        interpolation="nearest",
    )

    # Colorbar
    plt.colorbar(im, ax=ax, label=label)

    # Labels and title
    ax.set_xlabel("X (mm)", fontsize=12)
    ax.set_ylabel("Y (mm)", fontsize=12)

    if title is None:
        title = f"Scintillator Exit ({len(photons):,} photons)"
    ax.set_title(title, fontsize=14)

    # Add grid
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)

    # Equal aspect ratio
    ax.set_aspect("equal")

    # Tight layout
    fig.tight_layout()

    # Save if requested
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Saved image to: {output_path}")

    # Show if requested
    if show:
        plt.show()

    return fig, ax


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python plotter.py <transportedPhotons.bin> [output.png]")
        print()
        print("Example:")
        print("  python plotter.py data/run_000/transportedPhotons/photons.bin")
        print("  python plotter.py data/run_000/transportedPhotons/photons.bin output.png")
        sys.exit(1)

    transported_bin = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        image_transported_photons(
            transported_bin,
            bins=150,
            output_path=output_path,
            show=(output_path is None),  # Only show if not saving
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
