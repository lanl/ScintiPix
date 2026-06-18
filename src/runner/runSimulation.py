"""Thin simulation launcher built on validated `Simulation` config."""

from __future__ import annotations

from pathlib import Path
import re
import shlex
import subprocess
import sys

try:
    from src.common.logger import DEFAULT_RUN_LOG_FILENAME, get_logger, log_stage
    from src.config.macro import write_macro
    from src.models.simulation import Simulation
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.common.logger import DEFAULT_RUN_LOG_FILENAME, get_logger, log_stage
    from src.config.macro import write_macro
    from src.models.simulation import Simulation


_SIMULATED_EVENTS_PATTERN = re.compile(r"Simulated\s+(\d+)\s+events\b")


def _simulation_command(config: Simulation, macro_path: Path) -> list[str]:
    """Build subprocess command tokens from `config.geant4runner.binary` + macro."""

    try:
        tokens = shlex.split(config.geant4runner.binary)
    except ValueError as exc:
        raise ValueError(
            f"Could not parse `geant4runner.binary` into command tokens: {exc}"
        ) from exc
    if not tokens:
        raise ValueError(
            "`geant4runner.binary` did not resolve to an executable command."
        )
    return [*tokens, str(macro_path)]


def _simulation_total_events(config: Simulation) -> int | None:
    """Return total configured events for progress display, if available."""

    return config.geant4runner.number_of_particles


def _parse_simulated_events(line: str) -> int | None:
    """Extract aggregate simulated-event count from a Geant4 status line."""

    match = _SIMULATED_EVENTS_PATTERN.search(line)
    if match is None:
        return None
    return int(match.group(1))


def _binary_output_filename(base_path: Path) -> str:
    """Return the binary output filename (single .bin file)."""
    stem = base_path.stem or "output"
    return f"{stem}.bin"


def _has_binary_output(base_path: Path) -> bool:
    """Return true when the binary output file exists."""
    return base_path.exists()


def _expected_output_bases(config: Simulation) -> list[Path]:
    """Return configured base paths for enabled Geant4 output tables."""

    env = config.metadata.run_environment
    output = config.geant4runner.output
    paths: list[Path] = []
    if output.primaries:
        paths.append(Path(env.primaries_directory) / env.primaries_filename)
    if output.secondaries:
        paths.append(Path(env.secondaries_directory) / env.secondaries_filename)
    if output.photons:
        paths.append(Path(env.simulated_photons_directory) / env.photons_filename)
    return [path.resolve() for path in paths]


def _write_progress(current: int, total: int) -> None:
    """Render a simple in-terminal simulation progress bar."""

    if total <= 0:
        return
    clamped = min(current, total)
    width = 30
    fraction = clamped / total
    filled = int(width * fraction)
    bar = f"[{'#' * filled}{'-' * (width - filled)}]"
    percent = int(fraction * 100)
    sys.stderr.write(
        f"\rSimulation {bar} {percent:3d}% ({clamped}/{total} events)"
    )
    sys.stderr.flush()
    if clamped >= total:
        sys.stderr.write("\n")
        sys.stderr.flush()


def run(
    config: Simulation,
    *,
    dry_run: bool = False,
    log_filename: str | Path | None = None,
) -> subprocess.CompletedProcess[str] | None:
    """Launch a simulation from validated config.

    Preconditions:
    - the macro has already been written to the canonical macro path
    - any desired logging has already been configured by the caller

    Returns the raw subprocess result when executed, or ``None`` for dry runs.
    """

    run_environment = config.metadata.run_environment
    if run_environment.macro_directory is None:
        raise ValueError("Macro directory not configured in run environment")
    if run_environment.log_directory is None:
        raise ValueError("Log directory not configured in run environment")
    output = config.geant4runner.output
    if output.primaries and run_environment.primaries_directory is None:
        raise ValueError("Primaries directory not configured in run environment")
    if output.secondaries and run_environment.secondaries_directory is None:
        raise ValueError("Secondaries directory not configured in run environment")
    if output.photons and run_environment.simulated_photons_directory is None:
        raise ValueError("Simulated photons directory not configured in run environment")

    macro_filename = (
        f"{run_environment.simulation_run_id}_"
        f"{run_environment.sub_run_number:03d}.mac"
    )
    macro_path = (Path(run_environment.macro_directory) / macro_filename).resolve()
    output_bases = _expected_output_bases(config)

    if not macro_path.exists():
        raise FileNotFoundError(
            "Expected generated macro at "
            f"{macro_path}. Write the macro before calling `run(config)`."
        )
    if macro_path.is_dir():
        raise IsADirectoryError(
            "Resolved macro path is a directory, expected a file: "
            f"{macro_path}"
        )

    if log_filename is None:
        log_path = Path(run_environment.log_directory) / DEFAULT_RUN_LOG_FILENAME
    else:
        log_path = Path(log_filename)
        if not log_path.is_absolute() and log_path.parent == Path("."):
            log_path = Path(run_environment.log_directory) / log_path
    log_path = log_path.resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = _simulation_command(config, macro_path)
    total_events = (
        _simulation_total_events(config)
        if config.geant4runner.show_progress
        else None
    )

    logger = get_logger()
    if dry_run:
        return None

    last_progress = 0
    displayed_progress = False
    logger.info(f"[simulation] Command: {shlex.join(command)}")
    output_files = output_bases
    logger.info(
        "[simulation] Binary output files: "
        f"{', '.join(str(f) for f in output_files)}"
    )
    with log_stage("simulation"):
        with log_path.open("a", encoding="utf-8") as log_file:
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            ) as process:
                if process.stdout is None:
                    raise RuntimeError("Simulation process did not expose a stdout stream.")

                for line in process.stdout:
                    log_file.write(line)
                    log_file.flush()

                    if total_events is None:
                        continue
                    progress = _parse_simulated_events(line)
                    if progress is None or progress < last_progress:
                        continue
                    last_progress = progress
                    displayed_progress = True
                    _write_progress(progress, total_events)

                return_code = process.wait()

    if displayed_progress and total_events is not None and last_progress < total_events:
        sys.stderr.write("\n")
        sys.stderr.flush()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)

    completed = subprocess.CompletedProcess(command, return_code)
    if config.geant4runner.verify_output:
        missing_files = [
            str(output_file)
            for base, output_file in zip(output_bases, output_files, strict=True)
            if not _has_binary_output(base)
        ]
        if missing_files:
            raise FileNotFoundError(
                "Simulation finished but expected binary output files were not found: "
                + ", ".join(missing_files)
            )
    return completed


def run_simulation(
    config: Simulation,
    *,
    dry_run: bool = False,
    log_filename: str | Path | None = None,
) -> subprocess.CompletedProcess[str] | None:
    """Prepare and launch one simulation from validated config."""

    write_macro(config)
    completed = run(config, dry_run=dry_run, log_filename=log_filename)
    logger = get_logger()
    if completed is None:
        logger.info("[simulation] Dry run requested; skipping scintipix launch.")
        return None
    logger.info("[simulation] Completed.")
    return completed
