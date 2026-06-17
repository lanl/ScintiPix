"""Geant4 macro IO helpers for hierarchical :mod:`src.config.SimConfig`."""

from __future__ import annotations

from datetime import date as DateType
import math
from pathlib import Path
import shlex
import sys

try:
    from src.config.RunEnvironmentIO import (
        DEFAULT_OUTPUT_FILENAME_BASE,
        SIMULATED_PHOTONS_STAGE_DIR,
        TRANSPORT_PHOTONS_STAGE_DIR,
        prepare_run_environment,
        resolve_run_environment_directory,
        simulated_output_filename,
        split_sub_run_suffix,
        validate_run_environment,
    )
    from models.Simulation import SimConfig, default_sim_config
    from common.utilities import (
        _ENERGY_UNIT_TO_EV,
        _LENGTH_UNIT_TO_MM,
        _length_to_mm,
        _parse_density_to_g_cm3,
        _parse_energy_to_mev,
        _parse_length_tokens,
        _parse_numeric_list_with_optional_unit,
        _parse_scint_yield_to_per_mev,
        _parse_time_to_ns,
        _parse_vector3,
    )
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.config.RunEnvironmentIO import (
        DEFAULT_OUTPUT_FILENAME_BASE,
        SIMULATED_PHOTONS_STAGE_DIR,
        TRANSPORT_PHOTONS_STAGE_DIR,
        prepare_run_environment,
        resolve_run_environment_directory,
        simulated_output_filename,
        split_sub_run_suffix,
        validate_run_environment,
    )
    from models.Simulation import SimConfig, default_sim_config
    from common.utilities import (
        _ENERGY_UNIT_TO_EV,
        _LENGTH_UNIT_TO_MM,
        _length_to_mm,
        _parse_density_to_g_cm3,
        _parse_energy_to_mev,
        _parse_length_tokens,
        _parse_numeric_list_with_optional_unit,
        _parse_scint_yield_to_per_mev,
        _parse_time_to_ns,
        _parse_vector3,
    )

DEFAULT_OPTICAL_INTERFACE_THICKNESS_MM = 0.1
NS_PER_SECOND = 1_000_000_000.0
MM_PER_CM = 10.0


def _parse_scintillation_component_index(
    command: str,
    *,
    prefix: str,
) -> int | None:
    if not command.startswith(prefix):
        return None
    suffix = command[len(prefix) :].strip()
    if suffix not in {"1", "2", "3"}:
        return None
    return int(suffix) - 1


def _scintillation_profile_key_for_particle(particle: str) -> str | None:
    token = particle.strip().lower()
    if token in {"neutron", "n"}:
        return "neutron"
    if token in {"gamma", "g"}:
        return "gamma"
    return None


def source_commands(config: SimConfig) -> list[str]:
    gps = config.source.gps
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


def _source_area_cm2(config: SimConfig) -> float:
    radius_cm = config.source.gps.position.radius_mm / MM_PER_CM
    return math.pi * radius_cm * radius_cm


def _source_particle_rate_per_second(config: SimConfig) -> float:
    timing = config.source.timing
    if timing is None or timing.particle_flux is None:
        raise ValueError(
            "`source.timing.particle_flux` is required to derive source timing."
        )
    return timing.particle_flux * _source_area_cm2(config)


def _source_event_spacing_ns(config: SimConfig) -> float:
    particle_rate_per_second = _source_particle_rate_per_second(config)
    if particle_rate_per_second <= 0.0:
        raise ValueError("Derived source particle rate must be greater than zero.")
    return NS_PER_SECOND / particle_rate_per_second


def _source_particles_per_pulse(config: SimConfig) -> int:
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


def source_timing_commands(config: SimConfig) -> list[str]:
    timing = config.source.timing
    if timing is None:
        return []

    commands = [
        f"/source/timing/mode {timing.mode}",
        f"/source/timing/startTime {_format_macro_scalar(timing.start_time_ns)} ns",
    ]
    if timing.mode == "continuous":
        event_spacing_ns = _source_event_spacing_ns(config)
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
        particles_per_pulse = _source_particles_per_pulse(config)
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


def _default_import_template(macro_path: Path) -> SimConfig:
    payload = default_sim_config().model_dump(mode="python")
    metadata = payload["metadata"]
    run_environment = metadata["run_environment"]
    output_info = run_environment["output_info"]
    macro_run_id, macro_sub_run_number = split_sub_run_suffix(macro_path.stem)

    metadata["author"] = "Macro Import"
    metadata["date"] = DateType.today().isoformat()
    metadata["version"] = "imported"
    metadata["description"] = f"Imported from macro: {macro_path.name}"
    run_environment["simulation_run_id"] = macro_run_id
    run_environment["sub_run_number"] = (
        macro_sub_run_number if macro_sub_run_number is not None else 0
    )
    run_environment["working_directory"] = "data"
    run_environment["macro_directory"] = "macros"
    run_environment["log_directory"] = "logs"
    output_info["simulated_photons_dir"] = SIMULATED_PHOTONS_STAGE_DIR
    output_info["transported_photons_dir"] = TRANSPORT_PHOTONS_STAGE_DIR

    payload["simulation"] = None
    return SimConfig.model_validate(payload)


def from_macro(macro_path: str | Path, *, template: SimConfig | None = None) -> SimConfig:
    path = Path(macro_path)
    if not path.exists():
        raise FileNotFoundError(f"Macro file not found: {path}")

    base = template if template is not None else _default_import_template(path)
    payload = base.model_dump(mode="python")

    metadata = payload["metadata"]
    run_environment = metadata["run_environment"]
    scintillator = payload["scintillator"]
    scint_properties = scintillator.get("properties")
    if not isinstance(scint_properties, dict):
        scint_properties = {}
        scintillator["properties"] = scint_properties

    parsed_time_components = [
        {"time_constant": 0.0, "yield_fraction": 1.0},
        {"time_constant": 0.0, "yield_fraction": 0.0},
        {"time_constant": 0.0, "yield_fraction": 0.0},
    ]
    saw_time_component_command = False

    optical = payload["optical"]
    geometry = optical["geometry"]
    detector = optical["sensitive_detector_config"]
    simulation = payload.get("simulation")
    source = payload["source"]
    source_gps = source["gps"]
    source_timing = source.get("timing")
    position = source_gps["position"]
    angular = source_gps["angular"]
    energy = source_gps["energy"]
    runtime_controls = simulation.get("runtime_controls") if isinstance(simulation, dict) else None

    entrance_diameter_mm: float | None = None
    size_x_mm: float | None = None
    size_y_mm: float | None = None
    mask_radius_mm: float | None = None
    parsed_thickness_mm: float | None = None
    parsed_output_path: str | None = None
    parsed_output_filename: str | None = None
    parsed_output_runname: str | None = None
    parsed_source_timing_event_spacing_ns: float | None = None
    parsed_source_timing_neutrons_per_pulse: int | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        tokens = shlex.split(line, comments=False, posix=True)
        if not tokens:
            continue

        command = tokens[0]

        if command == "/output/format":
            raise ValueError(
                "Legacy command '/output/format' is no longer supported. HDF5 output is always enabled."
            )
        if command == "/output/path" and len(tokens) >= 2:
            parsed_output_path = tokens[1]
            continue
        if command == "/output/filename" and len(tokens) >= 2:
            parsed_output_filename = tokens[1]
            continue
        if command == "/output/runname" and len(tokens) >= 2:
            parsed_output_runname = tokens[1].strip()
            continue
        if command == "/control/verbose" and len(tokens) >= 2:
            if simulation is None:
                simulation = {}
                payload["simulation"] = simulation
            if runtime_controls is None:
                runtime_controls = {}
                simulation["runtime_controls"] = runtime_controls
            runtime_controls["control_verbose"] = int(tokens[1])
            continue
        if command == "/run/verbose" and len(tokens) >= 2:
            if simulation is None:
                simulation = {}
                payload["simulation"] = simulation
            if runtime_controls is None:
                runtime_controls = {}
                simulation["runtime_controls"] = runtime_controls
            runtime_controls["run_verbose"] = int(tokens[1])
            continue
        if command == "/event/verbose" and len(tokens) >= 2:
            if simulation is None:
                simulation = {}
                payload["simulation"] = simulation
            if runtime_controls is None:
                runtime_controls = {}
                simulation["runtime_controls"] = runtime_controls
            runtime_controls["event_verbose"] = int(tokens[1])
            continue
        if command == "/tracking/verbose" and len(tokens) >= 2:
            if simulation is None:
                simulation = {}
                payload["simulation"] = simulation
            if runtime_controls is None:
                runtime_controls = {}
                simulation["runtime_controls"] = runtime_controls
            runtime_controls["tracking_verbose"] = int(tokens[1])
            continue
        if command == "/run/printProgress" and len(tokens) >= 2:
            if simulation is None:
                simulation = {}
                payload["simulation"] = simulation
            if runtime_controls is None:
                runtime_controls = {}
                simulation["runtime_controls"] = runtime_controls
            runtime_controls["print_progress"] = int(tokens[1])
            continue
        if command == "/tracking/storeTrajectory" and len(tokens) >= 2:
            raw = tokens[1].strip().lower()
            if raw in {"1", "true", "yes", "on"}:
                parsed_store = True
            elif raw in {"0", "false", "no", "off"}:
                parsed_store = False
            else:
                raise ValueError(
                    "Command '/tracking/storeTrajectory' requires boolean-like token "
                    f"(0/1/true/false), got: {tokens[1]!r}"
                )
            if simulation is None:
                simulation = {}
                payload["simulation"] = simulation
            if runtime_controls is None:
                runtime_controls = {}
                simulation["runtime_controls"] = runtime_controls
            runtime_controls["store_trajectory"] = parsed_store
            continue
        if command == "/run/beamOn" and len(tokens) >= 2:
            try:
                particle_count = int(tokens[1])
            except ValueError as exc:
                raise ValueError(
                    f"Command '{command}' requires integer particle count, got: {tokens[1]!r}"
                ) from exc
            if particle_count <= 0:
                raise ValueError(
                    f"Command '{command}' requires positive particle count, got: {particle_count}"
                )
            if simulation is None:
                simulation = {}
                payload["simulation"] = simulation
            simulation["number_of_particles"] = particle_count
            continue

        if command.startswith("/source/timing/"):
            if source_timing is None:
                source_timing = {}
                source["timing"] = source_timing
            if command == "/source/timing/mode" and len(tokens) >= 2:
                source_timing["mode"] = tokens[1].strip().lower()
                continue
            if command == "/source/timing/startTime":
                source_timing["start_time_ns"] = _parse_time_to_ns(tokens, command)
                continue
            if command == "/source/timing/eventSpacing":
                parsed_source_timing_event_spacing_ns = _parse_time_to_ns(tokens, command)
                continue
            if command == "/source/timing/pulsePeriod":
                source_timing["pulse_period_ns"] = _parse_time_to_ns(tokens, command)
                continue
            if command == "/source/timing/neutronsPerPulse" and len(tokens) >= 2:
                parsed_source_timing_neutrons_per_pulse = int(tokens[1])
                continue
            if command == "/source/timing/pulseTimeOffset":
                source_timing["pulse_time_offset_ns"] = _parse_time_to_ns(tokens, command)
                continue
            if command == "/source/timing/pulseTimeWidth":
                source_timing["pulse_time_width_ns"] = _parse_time_to_ns(tokens, command)
                continue
            if command == "/source/timing/pulseShape" and len(tokens) >= 2:
                source_timing["pulse_shape"] = tokens[1].strip().lower()
                continue

        if command == "/gps/particle" and len(tokens) >= 2:
            source_gps["particle"] = tokens[1]
            continue
        if command == "/gps/pos/type" and len(tokens) >= 2:
            position["type"] = tokens[1]
            continue
        if command == "/gps/pos/shape" and len(tokens) >= 2:
            position["shape"] = tokens[1]
            continue
        if command == "/gps/pos/centre":
            if len(tokens) < 5:
                raise ValueError(f"Command '{command}' requires '<x> <y> <z> <unit>', got: {tokens!r}")
            x_mm = _length_to_mm(float(tokens[1]), tokens[4])
            y_mm = _length_to_mm(float(tokens[2]), tokens[4])
            z_mm = _length_to_mm(float(tokens[3]), tokens[4])
            position["center_mm"] = {"x_mm": x_mm, "y_mm": y_mm, "z_mm": z_mm}
            continue
        if command == "/gps/pos/radius":
            position["radius_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/gps/ang/type" and len(tokens) >= 2:
            angular["type"] = tokens[1]
            continue
        if command == "/gps/ang/rot1":
            x, y, z = _parse_vector3(tokens, command)
            angular["rot1"] = {"x": x, "y": y, "z": z}
            continue
        if command == "/gps/ang/rot2":
            x, y, z = _parse_vector3(tokens, command)
            angular["rot2"] = {"x": x, "y": y, "z": z}
            continue
        if command == "/gps/direction":
            x, y, z = _parse_vector3(tokens, command)
            angular["direction"] = {"x": x, "y": y, "z": z}
            continue
        if command == "/gps/ene/type" and len(tokens) >= 2:
            energy["type"] = tokens[1]
            if tokens[1].strip().lower() != "mono":
                energy.pop("mono_mev", None)
            continue
        if command == "/gps/ene/mono":
            energy["mono_mev"] = _parse_energy_to_mev(tokens, command)
            energy["type"] = "Mono"
            continue

        if command == "/scintillator/geom/material" and len(tokens) >= 2:
            scint_properties["name"] = tokens[1]
            continue
        if command == "/scintillator/geom/scintX":
            scintillator["dimension_mm"]["x_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/scintillator/geom/scintY":
            scintillator["dimension_mm"]["y_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/scintillator/geom/scintZ":
            scintillator["dimension_mm"]["z_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/scintillator/geom/posX":
            scintillator["position_mm"]["x_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/scintillator/geom/posY":
            scintillator["position_mm"]["y_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/scintillator/geom/posZ":
            scintillator["position_mm"]["z_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/scintillator/geom/maskRadius":
            mask_radius_mm = _parse_length_tokens(tokens, command)
            continue
        if command == "/scintillator/properties/density":
            scint_properties["density"] = _parse_density_to_g_cm3(tokens, command)
            continue
        if command == "/scintillator/properties/carbonAtoms" and len(tokens) >= 2:
            scint_properties["carbon_atoms"] = int(tokens[1])
            continue
        if command == "/scintillator/properties/hydrogenAtoms" and len(tokens) >= 2:
            scint_properties["hydrogen_atoms"] = int(tokens[1])
            continue
        if command == "/scintillator/properties/photonEnergy":
            values, unit = _parse_numeric_list_with_optional_unit(tokens, command)
            factor = _ENERGY_UNIT_TO_EV.get((unit or "eV").strip().lower())
            if factor is None:
                raise ValueError(f"Command '{command}' has unsupported energy unit: {unit!r}.")
            scint_properties["photon_energy"] = [value * factor for value in values]
            scint_properties["n_k_entries"] = len(values)
            continue
        if command == "/scintillator/properties/rIndex":
            values, unit = _parse_numeric_list_with_optional_unit(tokens, command)
            if unit is not None and unit.strip().lower() not in {"unitless", "none"}:
                raise ValueError(f"Command '{command}' does not support unit token {unit!r}.")
            scint_properties["r_index"] = values
            if "n_k_entries" not in scint_properties:
                scint_properties["n_k_entries"] = len(values)
            continue
        if command == "/scintillator/properties/absLength":
            values, unit = _parse_numeric_list_with_optional_unit(tokens, command)
            factor = _LENGTH_UNIT_TO_MM.get((unit or "cm").strip().lower())
            if factor is None:
                raise ValueError(f"Command '{command}' has unsupported length unit: {unit!r}.")
            scint_properties["abs_length"] = [(value * factor) / 10.0 for value in values]
            continue
        if command == "/scintillator/properties/scintSpectrum":
            values, unit = _parse_numeric_list_with_optional_unit(tokens, command)
            if unit is not None and unit.strip().lower() not in {"unitless", "none"}:
                raise ValueError(f"Command '{command}' does not support unit token {unit!r}.")
            scint_properties["scint_spectrum"] = values
            continue
        if command == "/scintillator/properties/scintYield":
            scint_properties["scint_yield"] = _parse_scint_yield_to_per_mev(tokens, command)
            continue
        if command == "/scintillator/properties/resolutionScale" and len(tokens) >= 2:
            scint_properties["resolution_scale"] = float(tokens[1])
            continue

        component_index = _parse_scintillation_component_index(command, prefix="/scintillator/properties/timeConstant")
        if component_index is not None:
            parsed_time_components[component_index]["time_constant"] = _parse_time_to_ns(tokens, command)
            saw_time_component_command = True
            continue
        component_index = _parse_scintillation_component_index(command, prefix="/scintillator/properties/yieldFraction")
        if component_index is not None:
            if len(tokens) < 2:
                raise ValueError(f"Command '{command}' requires scalar value token, got: {tokens!r}")
            try:
                parsed_time_components[component_index]["yield_fraction"] = float(tokens[1])
            except ValueError as exc:
                raise ValueError(f"Command '{command}' has non-numeric value token: {tokens[1]!r}") from exc
            saw_time_component_command = True
            continue
        if command in {"/scintillator/properties/timeConstant", "/scintillator/properties/yield1"}:
            raise ValueError(
                f"Legacy command '{command}' is no longer supported. "
                "Use `scintillator.properties.timeComponents.{default|neutron|gamma}` in YAML."
            )

        if command == "/optical_interface/geom/sizeX":
            size_x_mm = _parse_length_tokens(tokens, command)
            continue
        if command == "/optical_interface/geom/sizeY":
            size_y_mm = _parse_length_tokens(tokens, command)
            continue
        if command == "/optical_interface/geom/thickness":
            parsed_thickness_mm = _parse_length_tokens(tokens, command)
            continue
        if command == "/optical_interface/geom/posX":
            detector["position_mm"]["x_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/optical_interface/geom/posY":
            detector["position_mm"]["y_mm"] = _parse_length_tokens(tokens, command)
            continue
        if command == "/optical_interface/geom/posZ":
            detector["position_mm"]["z_mm"] = _parse_length_tokens(tokens, command)
            continue

    if parsed_thickness_mm is not None and not math.isclose(
        parsed_thickness_mm,
        DEFAULT_OPTICAL_INTERFACE_THICKNESS_MM,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise ValueError(
            "Loaded macro uses optical-interface thickness "
            f"{parsed_thickness_mm:g} mm, but hierarchical SimConfig currently does not model thickness explicitly."
        )

    if size_x_mm is not None and size_y_mm is not None:
        if not math.isclose(size_x_mm, size_y_mm, rel_tol=0.0, abs_tol=1.0e-9):
            raise ValueError(
                "Loaded macro has non-circular optical-interface size: "
                f"sizeX={size_x_mm:.6f} mm, sizeY={size_y_mm:.6f} mm."
            )
        entrance_diameter_mm = size_x_mm
    elif size_x_mm is not None:
        entrance_diameter_mm = size_x_mm
    elif size_y_mm is not None:
        entrance_diameter_mm = size_y_mm

    if entrance_diameter_mm is not None:
        geometry["entrance_diameter"] = entrance_diameter_mm

    if mask_radius_mm is not None:
        scintillator["mask_radius_mm"] = mask_radius_mm

    position.setdefault("type", "Plane")
    position.setdefault("shape", "Circle")
    energy.setdefault("type", "Mono")
    if energy.get("type", "").strip().lower() == "mono":
        energy.setdefault("mono_mev", 1.0)

    if parsed_output_runname is not None and parsed_output_runname.strip():
        run_environment["simulation_run_id"] = parsed_output_runname.strip()
    if parsed_output_path is not None:
        run_environment["working_directory"] = str(Path(parsed_output_path))
    if parsed_output_filename is not None:
        parsed_output_stem = Path(parsed_output_filename).stem
        base_stem, parsed_sub_run_number = split_sub_run_suffix(parsed_output_stem)
        if base_stem == DEFAULT_OUTPUT_FILENAME_BASE and parsed_sub_run_number is not None:
            run_environment["sub_run_number"] = parsed_sub_run_number

    if saw_time_component_command:
        time_components = scint_properties.get("time_components")
        if time_components is None:
            time_components = {}
        elif not isinstance(time_components, dict):
            raise ValueError(
                "`scintillator.properties.timeComponents` must be an object with `default`, `neutron`, and/or `gamma` keys."
            )
        profile_key = _scintillation_profile_key_for_particle(source_gps["particle"])
        if profile_key is None:
            profile_key = "default"
        time_components[profile_key] = parsed_time_components
        scint_properties["time_components"] = time_components

    if isinstance(source_timing, dict) and source_timing.get("particle_flux") is None:
        radius_mm = float(position["radius_mm"])
        source_area_cm2 = math.pi * (radius_mm / MM_PER_CM) ** 2
        timing_mode = str(source_timing.get("mode", "none")).strip().lower()
        if timing_mode == "continuous" and parsed_source_timing_event_spacing_ns is not None:
            particle_rate_per_second = NS_PER_SECOND / parsed_source_timing_event_spacing_ns
            source_timing["particle_flux"] = particle_rate_per_second / source_area_cm2
        if (
            timing_mode == "pulsed"
            and parsed_source_timing_neutrons_per_pulse is not None
            and source_timing.get("pulse_period_ns") is not None
        ):
            pulse_period_ns = float(source_timing["pulse_period_ns"])
            particle_rate_per_second = (
                parsed_source_timing_neutrons_per_pulse * NS_PER_SECOND / pulse_period_ns
            )
            source_timing["particle_flux"] = particle_rate_per_second / source_area_cm2

    return SimConfig.model_validate(payload)


def output_commands(config: SimConfig) -> list[str]:
    return [
        f"/output/path {resolve_run_environment_directory(config, 'data')}",
        f"/output/filename {Path(simulated_output_filename(config)).stem}",
        f"/output/runname {config.metadata.run_environment.simulation_run_id}",
    ]


def _format_float_list(values: list[float]) -> str:
    return ",".join(f"{value:g}" for value in values)


def _format_macro_scalar(value: float) -> str:
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    return text if text else "0"


def geometry_commands(config: SimConfig) -> list[str]:
    scint = config.scintillator
    optical = config.optical
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

    if scint.properties.density is not None:
        commands.append(f"/scintillator/properties/density {scint.properties.density:g} g/cm3")
    if scint.properties.carbon_atoms is not None:
        commands.append(f"/scintillator/properties/carbonAtoms {scint.properties.carbon_atoms}")
    if scint.properties.hydrogen_atoms is not None:
        commands.append(f"/scintillator/properties/hydrogenAtoms {scint.properties.hydrogen_atoms}")

    commands.append("/scintillator/properties/photonEnergy " f"{_format_float_list(scint.properties.photon_energy)} eV")
    commands.append("/scintillator/properties/rIndex " f"{_format_float_list(scint.properties.r_index)}")
    if scint.properties.abs_length is not None:
        commands.append("/scintillator/properties/absLength " f"{_format_float_list(scint.properties.abs_length)} cm")
    if scint.properties.scint_spectrum is not None:
        commands.append("/scintillator/properties/scintSpectrum " f"{_format_float_list(scint.properties.scint_spectrum)}")
    if scint.properties.scint_yield is not None:
        commands.append(f"/scintillator/properties/scintYield {scint.properties.scint_yield:g}")
    if scint.properties.resolution_scale is not None:
        commands.append("/scintillator/properties/resolutionScale " f"{scint.properties.resolution_scale:g}")

    _, selected_components = scint.properties.time_components.resolve_for_particle(config.source.gps.particle)
    for index, component in enumerate(selected_components, start=1):
        commands.append("/scintillator/properties/timeConstant" f"{index} {component.time_constant:g} ns")
        commands.append("/scintillator/properties/yieldFraction" f"{index} {component.yield_fraction:g}")

    if scint.mask_radius_mm > 0.0:
        commands.append(f"/scintillator/geom/maskRadius {scint.mask_radius_mm:g} mm")

    commands.extend(
        [
            f"/optical_interface/geom/sizeX {optical.geometry.entrance_diameter:g} mm",
            f"/optical_interface/geom/sizeY {optical.geometry.entrance_diameter:g} mm",
            f"/optical_interface/geom/thickness {DEFAULT_OPTICAL_INTERFACE_THICKNESS_MM:g} mm",
            f"/optical_interface/geom/posX {detector.position_mm.x_mm:g} mm",
            f"/optical_interface/geom/posY {detector.position_mm.y_mm:g} mm",
            f"/optical_interface/geom/posZ {detector.position_mm.z_mm:g} mm",
        ]
    )
    return commands


def macro_commands(
    config: SimConfig,
    *,
    include_output: bool = True,
    include_run_initialize: bool = True,
) -> list[str]:
    commands: list[str] = []
    if config.simulation is not None and config.simulation.runtime_controls is not None:
        runtime = config.simulation.runtime_controls
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
        commands.extend(output_commands(config))
    commands.extend(geometry_commands(config))
    if include_run_initialize:
        commands.append("/run/initialize")
    commands.extend(source_commands(config))
    commands.extend(source_timing_commands(config))
    if config.simulation is not None and config.simulation.number_of_particles is not None:
        commands.append(f"/run/beamOn {config.simulation.number_of_particles}")
    return commands


def write_macro(
    config: SimConfig,
    *,
    include_output: bool = True,
    include_run_initialize: bool = True,
    create_output_directories: bool = True,
    overwrite: bool = True,
) -> None:
    if create_output_directories:
        paths = prepare_run_environment(config)
    else:
        paths = validate_run_environment(
            config,
            targets=("data", "run_root", "macro"),
            create_directories=False,
        )

    path = paths.macro_file
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")

    payload = "\n".join(
        macro_commands(
            config,
            include_output=include_output,
            include_run_initialize=include_run_initialize,
        )
    )
    path.write_text(payload + "\n", encoding="utf-8")


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
