"""Unit tests for macro.py write-only API.

Tests verify that write_macro() and append_macro_line() work correctly.
These tests are intentionally minimal and focused on the public API only.
"""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


def _repo_root() -> Path:
    """Resolve repository root by searching parent directories."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "src").is_dir() and (parent / "pixi.toml").is_file():
            return parent
    raise RuntimeError("Could not resolve repository root from test path.")


# Ensure repository root is importable when this file is run directly.
sys.path.insert(0, str(_repo_root()))


def _create_minimal_simulation(temp_dir: Path):
    """Create a minimal valid Simulation model for testing."""
    from src.models.simulation import Simulation
    from src.models.scintillator import (
        Scintillator,
        ScintillatorProperties,
        ScintillatorComposition,
        ScintillatorElement,
        ScintillatorOpticalProperties,
        ScintillationTimeComponent,
        ScintillationTimeComponentsByExcitation,
    )
    from src.models.base import Vec3Mm, Size3Mm, Vec3
    from src.models.source import Source, SourceGps, GpsPosition, GpsAngular, GpsEnergy
    from src.models.optics import Optics, Lens, OpticalInterface
    from src.models.geant4runtime import Geant4RunTime, Geant4RuntimeControls
    from src.models.metadata import Metadata, WorkingDirectoryLayout

    # Create time components
    time_components = ScintillationTimeComponentsByExcitation(
        default=[
            ScintillationTimeComponent(time_constant=2.1, yield_fraction=1.0),
            ScintillationTimeComponent(time_constant=0.0, yield_fraction=0.0),
            ScintillationTimeComponent(time_constant=0.0, yield_fraction=0.0),
        ]
    )

    # Create scintillator
    scintillator = Scintillator(
        position_mm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=0.0),
        dimension_mm=Size3Mm(x_mm=100.0, y_mm=100.0, z_mm=20.0),
        mask_radius_mm=0.0,
        properties=ScintillatorProperties(
            name="EJ200",
            composition=ScintillatorComposition(
                density=1.023,
                elements=[
                    ScintillatorElement(symbol="H", mass_fraction=0.085294),
                    ScintillatorElement(symbol="C", mass_fraction=0.914706),
                ],
            ),
            optical=ScintillatorOpticalProperties(
                photon_energy=[2.8, 3.0, 3.2],
                r_index=[1.58, 1.59, 1.60],
                abs_length=[380.0, 380.0, 300.0],
                scint_spectrum=[0.2, 1.0, 0.2],
                n_k_entries=3,
                scint_yield=10000.0,
                resolution_scale=1.0,
                time_components=time_components,
            )
        )
    )

    # Create source
    source = Source(
        gps=SourceGps(
            particle="neutron",
            position=GpsPosition(
                type="Plane",
                shape="Circle",
                center_mm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=-100.0),
                radius_mm=10.0
            ),
            angular=GpsAngular(
                type="beam2d",
                rot1=Vec3(x=1.0, y=0.0, z=0.0),
                rot2=Vec3(x=0.0, y=1.0, z=0.0),
                direction=Vec3(x=0.0, y=0.0, z=1.0)
            ),
            energy=GpsEnergy(type="Mono", mono_mev=6.0)
        )
    )

    # Create optical config
    optical = Optics(
        lenses=[Lens(name="TestLens", primary=True, zmx_file="test.zmx")],
        interface=OpticalInterface(
            diameter_mm=60.55,
            position_mm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=210.05)
        )
    )

    # Create metadata with temp directory
    metadata = Metadata(
        author="Test",
        date="2026-06-17",
        version="test",
        description="Test simulation",
        run_environment=WorkingDirectoryLayout(
            SimulationRunID="test_run",
            WorkingDirectory=str(temp_dir),
            MacroDirectory="macros",
            LogDirectory="logs"
        )
    )

    # Create geant4runner
    geant4runner = Geant4RunTime(
        numberOfParticles=100,
        runtimeControls=Geant4RuntimeControls(
            controlVerbose=0,
            runVerbose=0,
            eventVerbose=0,
            trackingVerbose=0,
            printProgress=10
        )
    )

    return Simulation(
        scintillator=scintillator,
        source=source,
        optical=optical,
        metadata=metadata,
        geant4runner=geant4runner
    )


class MacroWriteTests(unittest.TestCase):
    """Tests for write_macro function."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load macro module or skip when dependencies are missing."""

        try:
            from src.config.macro import write_macro
        except ModuleNotFoundError as exc:
            missing_name = (getattr(exc, "name", "") or "").lower()
            message = str(exc).lower()
            if "pydantic" in missing_name or "pydantic" in message:
                raise unittest.SkipTest(
                    f"Missing dependency: {exc}. "
                    "Run in the project environment (for example: pixi run)."
                ) from exc
            raise

        cls.write_macro = staticmethod(write_macro)

    def test_write_macro_creates_file_with_commands(self) -> None:
        """write_macro should create a macro file with Geant4 commands."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            simulation = _create_minimal_simulation(tmp_path)

            macro_path = self.write_macro(
                simulation,
                include_output=True,
                include_run_initialize=True,
                create_directories=True,
                overwrite=True,
            )

            # Verify macro file was created
            self.assertTrue(macro_path.exists())
            self.assertTrue(macro_path.is_file())

            # Read and verify commands
            commands = macro_path.read_text(encoding="utf-8").strip().split('\n')
            self.assertGreater(len(commands), 0)

            # Verify key command categories are present
            self.assertTrue(any(cmd.startswith("/control/verbose") for cmd in commands))
            self.assertTrue(any(cmd == "/output/eventsPerOutput 1000" for cmd in commands))
            self.assertTrue(any(cmd == "/output/writePrimaries 1" for cmd in commands))
            self.assertTrue(any(cmd == "/output/writeSecondaries 1" for cmd in commands))
            self.assertTrue(any(cmd == "/output/writePhotons 1" for cmd in commands))
            self.assertTrue(any(cmd.startswith("/output/primariesFile ") for cmd in commands))
            self.assertTrue(any(cmd.startswith("/output/secondariesFile ") for cmd in commands))
            self.assertTrue(any(cmd.startswith("/output/photonsFile ") for cmd in commands))
            self.assertTrue(any(cmd.startswith("/scintillator/") for cmd in commands))
            self.assertTrue(any(cmd.startswith("/optical_interface/") for cmd in commands))
            self.assertTrue(any(cmd == "/run/initialize" for cmd in commands))
            self.assertTrue(any(cmd.startswith("/gps/") for cmd in commands))
            self.assertTrue(any(cmd.startswith("/run/beamOn") for cmd in commands))
            self.assertIn(
                "/scintillator/properties/elements C=0.914706,H=0.085294",
                commands,
            )
            self.assertFalse(
                any(cmd.startswith("/scintillator/properties/isotopes") for cmd in commands)
            )
            self.assertFalse(any("carbonAtoms" in cmd for cmd in commands))
            self.assertFalse(any("hydrogenAtoms" in cmd for cmd in commands))

    def test_write_macro_emits_sorted_enriched_composition(self) -> None:
        """Element and isotope commands should be complete and deterministic."""

        from src.models.scintillator import (
            ScintillatorComposition,
            ScintillatorElement,
            ScintillatorIsotope,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            simulation = _create_minimal_simulation(Path(tmp_dir))
            simulation.scintillator.properties.composition = ScintillatorComposition(
                density=2.42,
                elements=[
                    ScintillatorElement(symbol="Zn", mass_fraction=0.5),
                    ScintillatorElement(
                        symbol="Li",
                        mass_fraction=0.5,
                        isotopes=[
                            ScintillatorIsotope(mass_number=7, atom_fraction=0.05),
                            ScintillatorIsotope(mass_number=6, atom_fraction=0.95),
                        ],
                    ),
                ],
            )

            macro_path = self.write_macro(
                simulation,
                include_output=True,
                include_run_initialize=True,
                create_directories=True,
                overwrite=True,
            )
            commands = macro_path.read_text(encoding="utf-8").splitlines()

            self.assertIn(
                "/scintillator/properties/elements Li=0.5,Zn=0.5",
                commands,
            )
            self.assertIn(
                "/scintillator/properties/isotopes Li=6:0.95,7:0.05",
                commands,
            )

    def test_write_macro_filename_format(self) -> None:
        """write_macro should create files with correct naming format."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            simulation = _create_minimal_simulation(tmp_path)

            macro_path = self.write_macro(simulation, create_directories=True, overwrite=True)

            # Verify filename format: {run_id}_{sub_run:03d}.mac
            env = simulation.metadata.run_environment
            expected_name = f"{env.simulation_run_id}_{env.sub_run_number:03d}.mac"
            self.assertEqual(macro_path.name, expected_name)

    def test_write_macro_without_output_commands(self) -> None:
        """write_macro with include_output=False should omit output commands."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            simulation = _create_minimal_simulation(tmp_path)

            macro_path = self.write_macro(
                simulation,
                include_output=False,
                include_run_initialize=True,
                create_directories=True,
                overwrite=True,
            )

            commands = macro_path.read_text(encoding="utf-8").strip().split('\n')

            # Verify no output commands
            self.assertFalse(any(cmd.startswith("/output/") for cmd in commands))

            # But other commands should still be present
            self.assertTrue(any(cmd.startswith("/scintillator/") for cmd in commands))

    def test_write_macro_honors_disabled_output_tables(self) -> None:
        """write_macro should omit file commands for disabled output tables."""

        from src.models.geant4runtime import Geant4OutputConfig

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            simulation = _create_minimal_simulation(tmp_path)
            simulation.geant4runner.output = Geant4OutputConfig(
                primaries=True,
                secondaries=False,
                photons=False,
            )

            macro_path = self.write_macro(
                simulation,
                include_output=True,
                include_run_initialize=True,
                create_directories=True,
                overwrite=True,
            )

            commands = macro_path.read_text(encoding="utf-8").strip().split('\n')

            self.assertTrue(any(cmd == "/output/writePrimaries 1" for cmd in commands))
            self.assertTrue(any(cmd == "/output/writeSecondaries 0" for cmd in commands))
            self.assertTrue(any(cmd == "/output/writePhotons 0" for cmd in commands))
            self.assertTrue(any(cmd.startswith("/output/primariesFile ") for cmd in commands))
            self.assertFalse(any(cmd.startswith("/output/secondariesFile ") for cmd in commands))
            self.assertFalse(any(cmd.startswith("/output/photonsFile ") for cmd in commands))

    def test_write_macro_omits_resolution_target_by_default(self) -> None:
        """write_macro should omit resolution-target commands unless enabled."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            simulation = _create_minimal_simulation(tmp_path)

            macro_path = self.write_macro(
                simulation,
                include_output=True,
                include_run_initialize=True,
                create_directories=True,
                overwrite=True,
            )

            commands = macro_path.read_text(encoding="utf-8").strip().split('\n')

            self.assertFalse(
                any(
                    cmd.startswith("/scintillator/geom/resolutionTarget")
                    for cmd in commands
                )
            )

    def test_write_macro_emits_enabled_resolution_target_commands(self) -> None:
        """write_macro should emit Siemens star controls when enabled."""

        from src.models.geant4runtime import ResolutionTarget

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            simulation = _create_minimal_simulation(tmp_path)
            simulation.geant4runner.resolution_target = ResolutionTarget(
                enabled=True,
                outer_radius_mm=50.0,
                line_pairs=32,
            )

            macro_path = self.write_macro(
                simulation,
                include_output=True,
                include_run_initialize=True,
                create_directories=True,
                overwrite=True,
            )

            commands = macro_path.read_text(encoding="utf-8").strip().split('\n')

            self.assertIn("/scintillator/geom/resolutionTargetEnabled 1", commands)
            self.assertIn(
                "/scintillator/geom/resolutionTargetOuterRadius 50 mm",
                commands,
            )
            self.assertIn("/scintillator/geom/resolutionTargetLinePairs 32", commands)

    def test_write_macro_without_run_initialize(self) -> None:
        """write_macro with include_run_initialize=False should omit /run/initialize."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            simulation = _create_minimal_simulation(tmp_path)

            macro_path = self.write_macro(
                simulation,
                include_output=True,
                include_run_initialize=False,
                create_directories=True,
                overwrite=True,
            )

            commands = macro_path.read_text(encoding="utf-8").strip().split('\n')

            # Verify no /run/initialize command
            self.assertFalse(any(cmd == "/run/initialize" for cmd in commands))


class MacroAppendLineTests(unittest.TestCase):
    """Tests for append_macro_line function."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load macro module or skip when dependencies are missing."""

        try:
            from src.config.macro import append_macro_line
        except ModuleNotFoundError as exc:
            missing_name = (getattr(exc, "name", "") or "").lower()
            message = str(exc).lower()
            if "pydantic" in missing_name or "pydantic" in message:
                raise unittest.SkipTest(
                    f"Missing dependency: {exc}. "
                    "Run in the project environment (for example: pixi run)."
                ) from exc
            raise

        cls.append_macro_line = staticmethod(append_macro_line)

    def test_append_macro_line_appends_single_line(self) -> None:
        """append_macro_line should append one normalized line per call."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            macro_path = tmp_path / "append_test.mac"
            macro_path.write_text("/run/initialize\n", encoding="utf-8")

            self.append_macro_line(macro_path, "/vis/open OGL")
            self.append_macro_line(macro_path, "/vis/drawVolume\n")

            written_lines = macro_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                written_lines,
                ["/run/initialize", "/vis/open OGL", "/vis/drawVolume"],
            )

    def test_append_macro_line_rejects_embedded_newlines(self) -> None:
        """append_macro_line should reject payloads with embedded newlines."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            macro_path = tmp_path / "append_test.mac"
            macro_path.write_text("/run/initialize\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                self.append_macro_line(
                    macro_path, "/vis/open OGL\n/vis/drawVolume"
                )

            with self.assertRaises(ValueError):
                self.append_macro_line(
                    macro_path, "/vis/open OGL\r/vis/drawVolume"
                )

            written_lines = macro_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(written_lines, ["/run/initialize"])

    def test_append_macro_line_strips_trailing_newlines(self) -> None:
        """append_macro_line should strip trailing newlines from input."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            macro_path = tmp_path / "append_test.mac"
            macro_path.write_text("", encoding="utf-8")

            self.append_macro_line(macro_path, "/run/initialize\n")
            self.append_macro_line(macro_path, "/gps/particle neutron\r\n")

            written_lines = macro_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                written_lines,
                ["/run/initialize", "/gps/particle neutron"],
            )


if __name__ == "__main__":
    unittest.main()
