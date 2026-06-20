"""Write Geant4 macro files from simulation configuration.

This module converts Simulation models into Geant4 macro command files.

Public API:
    write_macro: Main entry point for writing macro files
    append_macro_line: Utility for appending commands to existing macros
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

try:
    from src.models.simulation import Simulation
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.models.simulation import Simulation

NS_PER_SECOND = 1_000_000_000.0
MM_PER_CM = 10.0


def _source_commands(simulation: Simulation) -> list[str]:
    """Generate GPS source configuration commands."""
    gps = simulation.source.gps
    position = gps.position
    angular = gps.angular
    energy = gps.energy

    commands = [
        f"/gps/particle {gps.particle}",
        f"/gps/pos/type {position.type}",
        f"/gps/pos/shape {position.shape}",
        (
            f"/gps/pos/centre {position.center_mm.x_mm:g} "
            f"{position.center_mm.y_mm:g} {position.center_mm.z_mm:g} mm"
        ),
        f"/gps/pos/radius {position.radius_mm:g} mm",
        f"/gps/ang/type {angular.type}",
        f"/gps/ang/rot1 {angular.rot1.x:g} {angular.rot1.y:g} {angular.rot1.z:g}",
        f"/gps/ang/rot2 {angular.rot2.x:g} {angular.rot2.y:g} {angular.rot2.z:g}",
        f"/gps/direction {angular.direction.x:g} {angular.direction.y:g} {angular.direction.z:g}",
        f"/gps/ene/type {energy.type}",
    ]

    if energy.type.strip().lower() == "mono":
        mono_mev = energy.mono_mev
        if mono_mev is None:
            raise ValueError(
                "`source.gps.energy.monoMeV` is required when `/gps/ene/type Mono`."
            )
        commands.append(f"/gps/ene/mono {mono_mev:g} MeV")

    return commands


def _source_area_cm2(config: Simulation) -> float:
    radius_cm = config.source.gps.position.radius_mm / MM_PER_CM
    return math.pi * radius_cm * radius_cm


def _source_particle_rate_per_second(config: Simulation) -> float:
    timing = config.source.timing
    if timing is None or timing.particle_flux is None:
        raise ValueError(
            "`source.timing.particle_flux` is required to derive source timing."
        )
    return timing.particle_flux * _source_area_cm2(config)


def _source_event_spacing_ns(config: Simulation) -> float:
    particle_rate_per_second = _source_particle_rate_per_second(config)
    if particle_rate_per_second <= 0.0:
        raise ValueError("Derived source particle rate must be greater than zero.")
    return NS_PER_SECOND / particle_rate_per_second


def _source_particles_per_pulse(config: Simulation) -> int:
    timing = config.source.timing
    if timing is None or timing.pulse_period_ns is None:
        raise ValueError(
            "`source.timing.pulse_period_ns` is required for pulsed source timing."
        )
    expected_particles = (
        _source_particle_rate_per_second(config)
        * timing.pulse_period_ns
        / NS_PER_SECOND
    )
    return max(1, int(math.ceil(expected_particles - 1.0e-12)))


def _source_timing_commands(simulation: Simulation) -> list[str]:
    """Generate source timing configuration commands."""
    timing = simulation.source.timing
    if timing is None:
        return []

    commands = [
        f"/source/timing/mode {timing.mode}",
        f"/source/timing/startTime {_format_macro_scalar(timing.start_time_ns)} ns",
    ]
    if timing.mode == "continuous":
        event_spacing_ns = _source_event_spacing_ns(simulation)
        commands.append(
            "/source/timing/eventSpacing "
            f"{_format_macro_scalar(event_spacing_ns)} ns"
        )
    if timing.mode == "pulsed":
        if timing.pulse_period_ns is None or timing.pulse_time_width_ns is None:
            raise ValueError(
                "`source.timing.pulse_period_ns`, "
                "`source.timing.particle_flux`, and "
                "`source.timing.pulse_time_width_ns` are required when mode is "
                "'pulsed'."
            )
        particles_per_pulse = _source_particles_per_pulse(simulation)
        commands.extend(
            [
                "/source/timing/pulsePeriod "
                f"{_format_macro_scalar(timing.pulse_period_ns)} ns",
                f"/source/timing/neutronsPerPulse {particles_per_pulse}",
                "/source/timing/pulseTimeOffset "
                f"{_format_macro_scalar(timing.pulse_time_offset_ns)} ns",
                "/source/timing/pulseTimeWidth "
                f"{_format_macro_scalar(timing.pulse_time_width_ns)} ns",
                f"/source/timing/pulseShape {timing.pulse_shape}",
            ]
        )
    return commands


def _format_float_list(values: list[float]) -> str:
    """Format list of floats as comma-separated string with minimal digits."""
    return ",".join(f"{value:g}" for value in values)


def _format_macro_scalar(value: float) -> str:
    """Format scalar float for macro with minimal decimal places."""
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _photon_culling_commands(simulation: Simulation) -> list[str]:
    """Generate photon culling optimization commands."""
    culling = simulation.geant4runner.photon_culling
    return [
        f"/photonCulling/enabled {1 if culling.enabled else 0}",
        f"/photonCulling/acceptanceAngleDeg {culling.acceptance_angle_deg:g}",
    ]


def _output_commands(simulation: Simulation) -> list[str]:
    """Generate explicit Geant4 output file commands."""
    env = simulation.metadata.run_environment
    output = simulation.geant4runner.output
    if output.primaries and env.primaries_directory is None:
        raise ValueError("Primaries directory not configured in run environment")
    if output.secondaries and env.secondaries_directory is None:
        raise ValueError("Secondaries directory not configured in run environment")
    if output.photons and env.simulated_photons_directory is None:
        raise ValueError("Simulated photons directory not configured in run environment")

    commands = [
        f"/output/eventsPerOutput {simulation.geant4runner.events_per_output}",
        f"/output/writePrimaries {1 if output.primaries else 0}",
        f"/output/writeSecondaries {1 if output.secondaries else 0}",
        f"/output/writePhotons {1 if output.photons else 0}",
    ]
    if output.primaries:
        commands.append(
            "/output/primariesFile "
            f"{Path(env.primaries_directory) / env.primaries_filename}"
        )
    if output.secondaries:
        commands.append(
            "/output/secondariesFile "
            f"{Path(env.secondaries_directory) / env.secondaries_filename}"
        )
    if output.photons:
        commands.append(
            "/output/photonsFile "
            f"{Path(env.simulated_photons_directory) / env.photons_filename}"
        )
    return commands


def _geometry_commands(simulation: Simulation) -> list[str]:
    """Generate scintillator and optical interface geometry commands."""
    scint = simulation.scintillator
    optical = simulation.optical
    if optical is None:
        raise ValueError("`optical` configuration is required for macro generation.")
    detector = optical.sensitive_detector_config
    if scint.properties is None:
        raise ValueError(
            "`scintillator.properties` is missing. "
            "Load config via `from_yaml(...)` with `catalogId` or provide explicit properties."
        )

    commands = [
        f"/scintillator/geom/material {scint.properties.name}",
        f"/scintillator/geom/scintX {scint.dimension_mm.x_mm:g} mm",
        f"/scintillator/geom/scintY {scint.dimension_mm.y_mm:g} mm",
        f"/scintillator/geom/scintZ {scint.dimension_mm.z_mm:g} mm",
        f"/scintillator/geom/posX {scint.position_mm.x_mm:g} mm",
        f"/scintillator/geom/posY {scint.position_mm.y_mm:g} mm",
        f"/scintillator/geom/posZ {scint.position_mm.z_mm:g} mm",
    ]

    # Access composition properties from nested structure
    if scint.properties.composition.density is not None:
        commands.append(f"/scintillator/properties/density {scint.properties.composition.density:g} g/cm3")
    if "C" in scint.properties.composition.atoms:
        commands.append(f"/scintillator/properties/carbonAtoms {scint.properties.composition.atoms['C']}")
    if "H" in scint.properties.composition.atoms:
        commands.append(f"/scintillator/properties/hydrogenAtoms {scint.properties.composition.atoms['H']}")

    # Access optical properties from nested structure
    scint_optical = scint.properties.optical
    commands.append("/scintillator/properties/photonEnergy " f"{_format_float_list(scint_optical.photon_energy)} eV")
    commands.append("/scintillator/properties/rIndex " f"{_format_float_list(scint_optical.r_index)}")
    if scint_optical.abs_length is not None:
        commands.append("/scintillator/properties/absLength " f"{_format_float_list(scint_optical.abs_length)} cm")
    if scint_optical.scint_spectrum is not None:
        commands.append("/scintillator/properties/scintSpectrum " f"{_format_float_list(scint_optical.scint_spectrum)}")
    if scint_optical.scint_yield is not None:
        commands.append(f"/scintillator/properties/scintYield {scint_optical.scint_yield:g}")
    if scint_optical.resolution_scale is not None:
        commands.append("/scintillator/properties/resolutionScale " f"{scint_optical.resolution_scale:g}")

    _, selected_components = scint_optical.time_components.resolve_for_particle(simulation.source.gps.particle)
    for index, component in enumerate(selected_components, start=1):
        commands.append("/scintillator/properties/timeConstant" f"{index} {component.time_constant:g} ns")
        commands.append("/scintillator/properties/yieldFraction" f"{index} {component.yield_fraction:g}")

    if scint.mask_radius_mm > 0.0:
        commands.append(f"/scintillator/geom/maskRadius {scint.mask_radius_mm:g} mm")

    resolution_target = simulation.geant4runner.resolution_target
    if resolution_target.enabled:
        commands.extend(
            [
                "/scintillator/geom/resolutionTargetEnabled 1",
                (
                    "/scintillator/geom/resolutionTargetOuterRadius "
                    f"{resolution_target.outer_radius_mm:g} mm"
                ),
                (
                    "/scintillator/geom/resolutionTargetLinePairs "
                    f"{resolution_target.line_pairs}"
                ),
            ]
        )

    commands.extend(
        [
            f"/optical_interface/geom/sizeX {optical.geometry.entrance_diameter:g} mm",
            f"/optical_interface/geom/sizeY {optical.geometry.entrance_diameter:g} mm",
            "/optical_interface/geom/thickness 0.1 mm",
            f"/optical_interface/geom/posX {detector.position_mm.x_mm:g} mm",
            f"/optical_interface/geom/posY {detector.position_mm.y_mm:g} mm",
            f"/optical_interface/geom/posZ {detector.position_mm.z_mm:g} mm",
        ]
    )
    return commands


def _macro_commands(
    simulation: Simulation,
    *,
    include_output: bool = True,
    include_run_initialize: bool = True,
) -> list[str]:
    """Generate complete macro command list from simulation configuration."""
    commands: list[str] = []
    if simulation.geant4runner is not None and simulation.geant4runner.runtime_controls is not None:
        runtime = simulation.geant4runner.runtime_controls
        if runtime.control_verbose is not None:
            commands.append(f"/control/verbose {runtime.control_verbose}")
        if runtime.run_verbose is not None:
            commands.append(f"/run/verbose {runtime.run_verbose}")
        if runtime.event_verbose is not None:
            commands.append(f"/event/verbose {runtime.event_verbose}")
        if runtime.tracking_verbose is not None:
            commands.append(f"/tracking/verbose {runtime.tracking_verbose}")
        if runtime.print_progress is not None:
            commands.append(f"/run/printProgress {runtime.print_progress}")
        if runtime.store_trajectory is not None:
            commands.append(f"/tracking/storeTrajectory {1 if runtime.store_trajectory else 0}")

    if include_output:
        commands.extend(_output_commands(simulation))
    commands.extend(_photon_culling_commands(simulation))
    commands.extend(_geometry_commands(simulation))
    if include_run_initialize:
        commands.append("/run/initialize")
    commands.extend(_source_commands(simulation))
    commands.extend(_source_timing_commands(simulation))
    if simulation.geant4runner is not None and simulation.geant4runner.number_of_particles is not None:
        commands.append(f"/run/beamOn {simulation.geant4runner.number_of_particles}")
    return commands


def write_macro(
    simulation: Simulation,
    *,
    include_output: bool = True,
    include_run_initialize: bool = True,
    create_directories: bool = True,
    overwrite: bool = True,
) -> Path:
    """Write Geant4 macro file from simulation configuration.

    Args:
        simulation: The simulation configuration
        include_output: Include explicit output file commands.
        include_run_initialize: Include /run/initialize command
        create_directories: Create output directories if they don't exist
        overwrite: Overwrite existing macro file if it exists

    Returns:
        Path to the written macro file
    """
    if create_directories:
        simulation.metadata.run_environment.create_directories()

    env = simulation.metadata.run_environment
    if env.macro_directory is None:
        raise ValueError("Macro directory not configured in run environment")
    macro_path = (
        Path(env.macro_directory)
        / f"{env.simulation_run_id}_{env.sub_run_number:03d}.mac"
    )
    if macro_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {macro_path}")

    commands = _macro_commands(
        simulation,
        include_output=include_output,
        include_run_initialize=include_run_initialize,
    )
    payload = "\n".join(commands)
    macro_path.write_text(payload + "\n", encoding="utf-8")

    return macro_path


def append_macro_line(macro_file: str | Path, string_to_append: str) -> None:
    path = Path(macro_file)
    if path.exists() and path.is_dir():
        raise IsADirectoryError(f"Macro target is a directory, not a file: {path}")
    if not path.parent.exists():
        raise FileNotFoundError(f"Macro parent directory does not exist: {path.parent}")

    normalized = string_to_append.rstrip("\r\n")
    if "\n" in normalized or "\r" in normalized:
        raise ValueError(
            "append_macro_line expects a single line; newline characters are "
            "not allowed in `string_to_append`."
        )

    with path.open("a", encoding="utf-8") as handle:
        handle.write(normalized + "\n")


__all__ = ["write_macro", "append_macro_line"]
