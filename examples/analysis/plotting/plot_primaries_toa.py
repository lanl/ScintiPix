"""Plot primary-particle time-of-arrival from ScintiPix primaries Parquet output."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

TOA_COLUMN = "primary_interaction_time_ns"
SPECIES_COLUMN = "primary_species"


def resolve_primaries_path(path: Path) -> Path:
    """Resolve a primaries Parquet file from a file, primaries dir, or run dir."""

    if path.is_file():
        return path

    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Input path is not a file or directory: {path}")

    preferred_candidates = [
        path / "primaries.parquet",
        path / "primaries" / "primaries.parquet",
    ]
    for candidate in preferred_candidates:
        if candidate.is_file():
            return candidate

    parquet_files = sorted(path.glob("*.parquet"))
    if len(parquet_files) == 1:
        return parquet_files[0]
    if len(parquet_files) > 1:
        raise ValueError(
            "Multiple Parquet files found; pass the primaries file explicitly: "
            + ", ".join(str(file) for file in parquet_files)
        )

    raise FileNotFoundError(
        "Could not find primaries Parquet output. Expected either "
        f"{path / 'primaries.parquet'} or {path / 'primaries' / 'primaries.parquet'}."
    )


def read_primary_toa_ns(
    primaries_path: Path,
    *,
    species: str | None,
    column: str,
) -> np.ndarray:
    """Read finite primary time-of-arrival values from a primaries Parquet file."""

    columns = [column]
    if species is not None:
        columns.append(SPECIES_COLUMN)

    try:
        primaries = pd.read_parquet(primaries_path, columns=columns)
    except Exception as exc:
        raise RuntimeError(f"Failed to read {primaries_path}: {exc}") from exc

    if column not in primaries.columns:
        raise KeyError(f"{primaries_path} is missing required column {column!r}")

    if species is not None:
        if SPECIES_COLUMN not in primaries.columns:
            raise KeyError(
                f"{primaries_path} is missing required column {SPECIES_COLUMN!r}"
            )
        species_values = primaries[SPECIES_COLUMN].astype(str).str.lower()
        primaries = primaries[species_values == species.lower()]

    values = primaries[column].to_numpy(dtype=float, copy=False)
    values = values[np.isfinite(values)]
    if values.size == 0:
        details = f" for species {species!r}" if species is not None else ""
        raise ValueError(f"No finite {column!r} values found in {primaries_path}{details}.")
    return values


def plot_primary_toa(
    toa_ns: np.ndarray,
    *,
    bins: int,
    time_range: tuple[float, float] | None,
    relative: bool,
    log_y: bool,
    title: str,
) -> tuple[plt.Figure, plt.Axes]:
    """Create a primary time-of-arrival histogram."""

    values = np.asarray(toa_ns, dtype=float)
    x_label = "primary interaction time / TOA (ns)"
    if relative:
        values = values - float(np.min(values))
        x_label = "primary interaction time from first observed primary (ns)"

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(
        values,
        bins=bins,
        range=time_range,
        color="#356a8a",
        edgecolor="black",
        linewidth=0.45,
        alpha=0.85,
    )
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel("primary count")
    if log_y:
        ax.set_yscale("log")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    return fig, ax


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot a histogram of primary-particle time-of-arrival from ScintiPix "
            "primaries Parquet output."
        )
    )
    parser.add_argument(
        "input",
        type=Path,
        help=(
            "Primaries .parquet file, primaries output directory, or run directory "
            "containing primaries/primaries.parquet."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional image path. If omitted, the plot is shown interactively.",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=100,
        help="Number of histogram bins. Default: 100.",
    )
    parser.add_argument(
        "--range",
        dest="time_range",
        type=float,
        nargs=2,
        metavar=("MIN_NS", "MAX_NS"),
        help="Optional histogram time range in ns.",
    )
    parser.add_argument(
        "--species",
        help="Optional primary_species filter, for example neutron.",
    )
    parser.add_argument(
        "--column",
        default=TOA_COLUMN,
        help=f"Time column to plot. Default: {TOA_COLUMN}.",
    )
    parser.add_argument(
        "--relative",
        action="store_true",
        help="Subtract the first observed primary time so the histogram starts near 0 ns.",
    )
    parser.add_argument(
        "--log-y",
        action="store_true",
        help="Use a logarithmic y axis.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show the plot even when --output is provided.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    primaries_path = resolve_primaries_path(args.input)
    toa_ns = read_primary_toa_ns(
        primaries_path,
        species=args.species,
        column=args.column,
    )

    title = "Primary Time-of-Arrival"
    if args.species is not None:
        title += f" ({args.species})"

    fig, _ = plot_primary_toa(
        toa_ns,
        bins=args.bins,
        time_range=tuple(args.time_range) if args.time_range is not None else None,
        relative=args.relative,
        log_y=args.log_y,
        title=title,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=150)
        print(f"Wrote {args.output}")

    if args.show or args.output is None:
        plt.show()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
