"""Unit tests for src.config.yaml module."""

from pathlib import Path
import tempfile

import pytest
import yaml as pyyaml

from src.config.yaml import from_yaml, write_yaml
from src.models.simulation import Simulation
from src.models.source import Source, SourceGps, GpsPosition, GpsEnergy
from src.models.scintillator import (
    Scintillator,
    ScintillatorComposition,
    ScintillatorElement,
    ScintillatorOpticalProperties,
    ScintillatorProperties,
    ScintillationTimeComponentsByExcitation,
    ScintillationTimeComponent,
)
from src.models.geant4runtime import Geant4RunTime, Geant4RuntimeControls
from src.models.metadata import Metadata, WorkingDirectoryLayout
from src.models.base import Vec3Mm, Size3Mm


class TestFromYaml:
    """Tests for from_yaml function."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading a valid YAML file."""
        yaml_file = tmp_path / "test_config.yaml"
        yaml_content = """
source:
  gps:
    particle: neutron
    position:
      centerMm: {x_mm: 0.0, y_mm: 0.0, z_mm: -100.0}
      radiusMm: 10.0
    energy:
      type: Mono
      monoMeV: 6.0

scintillator:
  position_mm: {x_mm: 0.0, y_mm: 0.0, z_mm: 0.0}
  dimension_mm: {x_mm: 100.0, y_mm: 100.0, z_mm: 20.0}
  properties:
    name: TestScint
    composition:
      density: 1.023
      elements:
        - {symbol: C, massFraction: 0.914706}
        - {symbol: H, massFraction: 0.085294}
    optical:
      photonEnergy: [2.0, 3.0, 4.0]
      rIndex: [1.58, 1.58, 1.58]
      nKEntries: 3
      timeComponents:
        default:
          - {timeConstant: 2.4, yieldFraction: 1.0}
          - {timeConstant: 0.0, yieldFraction: 0.0}
          - {timeConstant: 0.0, yieldFraction: 0.0}

geant4runner:
  numberOfParticles: 1000
  binary: scintipix
  resolutionTarget:
    resolutionTargetEnabled: true
    resolutionTargetOuterRadiusMm: 50.0
    resolutionTargetLinePairs: 32

metadata:
  author: Test Author
  date: "2026-06-16"
  version: v1.0
  description: Test configuration
  RunEnvironment:
    SimulationRunID: test_run
"""
        yaml_file.write_text(yaml_content)

        simulation = from_yaml(yaml_file)

        assert isinstance(simulation, Simulation)
        assert simulation.source.gps.particle == "neutron"
        assert simulation.scintillator.properties.name == "TestScint"
        assert simulation.geant4runner.number_of_particles == 1000
        assert simulation.geant4runner.resolution_target.enabled is True
        assert simulation.geant4runner.resolution_target.outer_radius_mm == 50.0
        assert simulation.geant4runner.resolution_target.line_pairs == 32
        assert simulation.metadata.author == "Test Author"

    def test_load_nonexistent_file(self):
        """Test that loading a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="YAML config file not found"):
            from_yaml("/nonexistent/path/to/file.yaml")

    def test_load_invalid_yaml_not_dict(self, tmp_path):
        """Test that loading YAML with non-dict top level raises ValueError."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("- item1\n- item2\n")

        with pytest.raises(ValueError, match="must be a mapping/object at top level"):
            from_yaml(yaml_file)

    def test_load_empty_yaml(self, tmp_path):
        """Test that loading empty YAML raises validation error."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        with pytest.raises(Exception):  # Will raise pydantic ValidationError
            from_yaml(yaml_file)

    def test_load_yaml_with_missing_required_fields(self, tmp_path):
        """Test that missing required fields raises validation error."""
        yaml_file = tmp_path / "incomplete.yaml"
        yaml_content = """
source:
  gps:
    particle: neutron
"""
        yaml_file.write_text(yaml_content)

        with pytest.raises(Exception):  # Will raise pydantic ValidationError
            from_yaml(yaml_file)


class TestWriteYaml:
    """Tests for write_yaml function."""

    def test_write_valid_simulation(self, tmp_path):
        """Test writing a valid Simulation to YAML."""
        yaml_file = tmp_path / "output.yaml"

        # Create a minimal valid Simulation
        simulation = Simulation(
            source=Source(
                gps=SourceGps(
                    particle="neutron",
                    position=GpsPosition(
                        centerMm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=-100.0),
                        radiusMm=10.0,
                    ),
                    energy=GpsEnergy(type="Mono", monoMeV=6.0),
                )
            ),
            scintillator=Scintillator(
                position_mm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=0.0),
                dimension_mm=Size3Mm(x_mm=100.0, y_mm=100.0, z_mm=20.0),
                properties=ScintillatorProperties(
                    name="TestScint",
                    composition=ScintillatorComposition(
                        density=1.023,
                        elements=[
                            ScintillatorElement(symbol="C", mass_fraction=0.914706),
                            ScintillatorElement(symbol="H", mass_fraction=0.085294),
                        ],
                    ),
                    optical=ScintillatorOpticalProperties(
                        photonEnergy=[2.0, 3.0, 4.0],
                        rIndex=[1.58, 1.58, 1.58],
                        nKEntries=3,
                        timeComponents=ScintillationTimeComponentsByExcitation(
                            default=[
                                ScintillationTimeComponent(
                                    timeConstant=2.4, yieldFraction=1.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                            ]
                        ),
                    ),
                ),
            ),
            geant4runner=Geant4RunTime(
                numberOfParticles=1000,
                binary="scintipix",
            ),
            metadata=Metadata(
                author="Test Author",
                date="2026-06-16",
                version="v1.0",
                description="Test configuration",
                RunEnvironment=WorkingDirectoryLayout(
                    SimulationRunID="test_run",
                ),
            ),
        )

        write_yaml(simulation, yaml_file)

        assert yaml_file.exists()

        # Verify it can be read back
        loaded = from_yaml(yaml_file)
        assert loaded.source.gps.particle == "neutron"
        assert loaded.geant4runner.number_of_particles == 1000

    def test_write_creates_parent_directories(self, tmp_path):
        """Test that write_yaml creates parent directories if needed."""
        yaml_file = tmp_path / "nested" / "dir" / "config.yaml"

        simulation = Simulation(
            source=Source(
                gps=SourceGps(
                    particle="neutron",
                    position=GpsPosition(
                        centerMm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=-100.0),
                        radiusMm=10.0,
                    ),
                    energy=GpsEnergy(type="Mono", monoMeV=6.0),
                )
            ),
            scintillator=Scintillator(
                position_mm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=0.0),
                dimension_mm=Size3Mm(x_mm=100.0, y_mm=100.0, z_mm=20.0),
                properties=ScintillatorProperties(
                    name="TestScint",
                    composition=ScintillatorComposition(
                        density=1.023,
                        elements=[
                            ScintillatorElement(symbol="C", mass_fraction=0.914706),
                            ScintillatorElement(symbol="H", mass_fraction=0.085294),
                        ],
                    ),
                    optical=ScintillatorOpticalProperties(
                        photonEnergy=[2.0, 3.0, 4.0],
                        rIndex=[1.58, 1.58, 1.58],
                        nKEntries=3,
                        timeComponents=ScintillationTimeComponentsByExcitation(
                            default=[
                                ScintillationTimeComponent(
                                    timeConstant=2.4, yieldFraction=1.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                            ]
                        ),
                    ),
                ),
            ),
            geant4runner=Geant4RunTime(
                numberOfParticles=1000,
                binary="scintipix",
            ),
            metadata=Metadata(
                author="Test Author",
                date="2026-06-16",
                version="v1.0",
                description="Test configuration",
                RunEnvironment=WorkingDirectoryLayout(
                    SimulationRunID="test_run",
                ),
            ),
        )

        write_yaml(simulation, yaml_file)

        assert yaml_file.exists()
        assert yaml_file.parent.exists()

    def test_write_refuses_to_overwrite_without_flag(self, tmp_path):
        """Test that write_yaml refuses to overwrite existing file when overwrite=False."""
        yaml_file = tmp_path / "existing.yaml"
        yaml_file.write_text("existing content")

        simulation = Simulation(
            source=Source(
                gps=SourceGps(
                    particle="neutron",
                    position=GpsPosition(
                        centerMm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=-100.0),
                        radiusMm=10.0,
                    ),
                    energy=GpsEnergy(type="Mono", monoMeV=6.0),
                )
            ),
            scintillator=Scintillator(
                position_mm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=0.0),
                dimension_mm=Size3Mm(x_mm=100.0, y_mm=100.0, z_mm=20.0),
                properties=ScintillatorProperties(
                    name="TestScint",
                    composition=ScintillatorComposition(
                        density=1.023,
                        elements=[
                            ScintillatorElement(symbol="C", mass_fraction=0.914706),
                            ScintillatorElement(symbol="H", mass_fraction=0.085294),
                        ],
                    ),
                    optical=ScintillatorOpticalProperties(
                        photonEnergy=[2.0, 3.0, 4.0],
                        rIndex=[1.58, 1.58, 1.58],
                        nKEntries=3,
                        timeComponents=ScintillationTimeComponentsByExcitation(
                            default=[
                                ScintillationTimeComponent(
                                    timeConstant=2.4, yieldFraction=1.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                            ]
                        ),
                    ),
                ),
            ),
            geant4runner=Geant4RunTime(
                numberOfParticles=1000,
                binary="scintipix",
            ),
            metadata=Metadata(
                author="Test Author",
                date="2026-06-16",
                version="v1.0",
                description="Test configuration",
                RunEnvironment=WorkingDirectoryLayout(
                    SimulationRunID="test_run",
                ),
            ),
        )

        with pytest.raises(FileExistsError, match="Refusing to overwrite"):
            write_yaml(simulation, yaml_file, overwrite=False)

    def test_write_overwrites_with_flag(self, tmp_path):
        """Test that write_yaml overwrites existing file when overwrite=True."""
        yaml_file = tmp_path / "existing.yaml"
        yaml_file.write_text("existing content")

        simulation = Simulation(
            source=Source(
                gps=SourceGps(
                    particle="neutron",
                    position=GpsPosition(
                        centerMm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=-100.0),
                        radiusMm=10.0,
                    ),
                    energy=GpsEnergy(type="Mono", monoMeV=6.0),
                )
            ),
            scintillator=Scintillator(
                position_mm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=0.0),
                dimension_mm=Size3Mm(x_mm=100.0, y_mm=100.0, z_mm=20.0),
                properties=ScintillatorProperties(
                    name="TestScint",
                    composition=ScintillatorComposition(
                        density=1.023,
                        elements=[
                            ScintillatorElement(symbol="C", mass_fraction=0.914706),
                            ScintillatorElement(symbol="H", mass_fraction=0.085294),
                        ],
                    ),
                    optical=ScintillatorOpticalProperties(
                        photonEnergy=[2.0, 3.0, 4.0],
                        rIndex=[1.58, 1.58, 1.58],
                        nKEntries=3,
                        timeComponents=ScintillationTimeComponentsByExcitation(
                            default=[
                                ScintillationTimeComponent(
                                    timeConstant=2.4, yieldFraction=1.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                            ]
                        ),
                    ),
                ),
            ),
            geant4runner=Geant4RunTime(
                numberOfParticles=1000,
                binary="scintipix",
            ),
            metadata=Metadata(
                author="Test Author",
                date="2026-06-16",
                version="v1.0",
                description="Test configuration",
                RunEnvironment=WorkingDirectoryLayout(
                    SimulationRunID="test_run",
                ),
            ),
        )

        write_yaml(simulation, yaml_file, overwrite=True)

        content = yaml_file.read_text()
        assert "Test Author" in content
        assert "existing content" not in content


class TestRoundTrip:
    """Tests for round-trip YAML loading and saving."""

    def test_round_trip_preserves_data(self, tmp_path):
        """Test that loading and saving preserves all data."""
        original_file = tmp_path / "original.yaml"
        roundtrip_file = tmp_path / "roundtrip.yaml"

        # Create and save original
        simulation = Simulation(
            source=Source(
                gps=SourceGps(
                    particle="gamma",
                    position=GpsPosition(
                        centerMm=Vec3Mm(x_mm=1.0, y_mm=2.0, z_mm=-50.0),
                        radiusMm=15.0,
                    ),
                    energy=GpsEnergy(type="Mono", monoMeV=4.5),
                )
            ),
            scintillator=Scintillator(
                catalogId="EJ200",
                position_mm=Vec3Mm(x_mm=0.0, y_mm=0.0, z_mm=0.0),
                dimension_mm=Size3Mm(x_mm=50.0, y_mm=50.0, z_mm=10.0),
                maskRadius=5.0,
                properties=ScintillatorProperties(
                    name="EJ200",
                    composition=ScintillatorComposition(
                        density=1.023,
                        elements=[
                            ScintillatorElement(symbol="C", mass_fraction=0.914706),
                            ScintillatorElement(symbol="H", mass_fraction=0.085294),
                        ],
                    ),
                    optical=ScintillatorOpticalProperties(
                        photonEnergy=[2.0, 3.0, 4.0],
                        rIndex=[1.58, 1.58, 1.58],
                        nKEntries=3,
                        scintYield=10000.0,
                        timeComponents=ScintillationTimeComponentsByExcitation(
                            default=[
                                ScintillationTimeComponent(
                                    timeConstant=2.1, yieldFraction=1.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                                ScintillationTimeComponent(
                                    timeConstant=0.0, yieldFraction=0.0
                                ),
                            ]
                        ),
                    ),
                ),
            ),
            geant4runner=Geant4RunTime(
                numberOfParticles=5000,
                binary="scintipix",
                showProgress=True,
                runtimeControls=Geant4RuntimeControls(
                    controlVerbose=1,
                    printProgress=100,
                ),
            ),
            metadata=Metadata(
                author="Round Trip Test",
                date="2026-06-16",
                version="v2.0",
                description="Round trip test configuration",
                RunEnvironment=WorkingDirectoryLayout(
                    SimulationRunID="roundtrip_test",
                    SubRunNumber=5,
                ),
            ),
        )

        write_yaml(simulation, original_file)

        # Load and save again
        loaded = from_yaml(original_file)
        write_yaml(loaded, roundtrip_file)

        # Load the roundtrip version
        final = from_yaml(roundtrip_file)

        # Verify key fields preserved
        assert final.source.gps.particle == "gamma"
        assert final.source.gps.position.center_mm.x_mm == 1.0
        assert final.source.gps.energy.mono_mev == 4.5
        assert final.scintillator.catalog_id == "EJ200"
        assert final.scintillator.mask_radius_mm == 5.0
        assert final.scintillator.properties.composition.density == 1.023
        assert final.geant4runner.number_of_particles == 5000
        assert final.geant4runner.runtime_controls.control_verbose == 1
        assert final.metadata.author == "Round Trip Test"
        assert final.metadata.run_environment.sub_run_number == 5


class TestSourceCatalogHydration:
    """Tests that a `source.catalogId` reference is hydrated on load."""

    @staticmethod
    def _scintillator_and_metadata_block() -> str:
        """Inline scintillator and metadata shared by the hydration configs."""
        return """
scintillator:
  position_mm: {x_mm: 0.0, y_mm: 0.0, z_mm: 0.0}
  dimension_mm: {x_mm: 100.0, y_mm: 100.0, z_mm: 20.0}
  properties:
    name: TestScint
    composition:
      density: 1.023
      elements:
        - {symbol: C, massFraction: 0.914706}
        - {symbol: H, massFraction: 0.085294}
    optical:
      photonEnergy: [2.0, 3.0, 4.0]
      rIndex: [1.58, 1.58, 1.58]
      nKEntries: 3
      timeComponents:
        default:
          - {timeConstant: 2.4, yieldFraction: 1.0}
          - {timeConstant: 0.0, yieldFraction: 0.0}
          - {timeConstant: 0.0, yieldFraction: 0.0}

geant4runner:
  numberOfParticles: 100
  binary: scintipix

metadata:
  author: Test Author
  date: "2026-06-16"
  version: v1.0
  description: Test configuration
  RunEnvironment:
    SimulationRunID: test_run
"""

    def test_catalog_id_hydrates_intrinsic_fields(self, tmp_path):
        """A position-only source with catalogId fills particle/angular/energy/gamma."""
        yaml_file = tmp_path / "ambe_source.yaml"
        yaml_file.write_text(
            """
source:
  catalogId: AmBe
  gps:
    position:
      centerMm: {x_mm: 0.0, y_mm: 0.0, z_mm: -100.0}
      radiusMm: 10.0
"""
            + self._scintillator_and_metadata_block()
        )

        simulation = from_yaml(yaml_file)

        assert simulation.source.catalog_id == "AmBe"
        assert simulation.source.gps.particle == "neutron"
        assert simulation.source.gps.angular.type == "iso"
        assert simulation.source.gps.energy.type == "AmBe"
        assert simulation.source.correlated_gamma is not None
        assert simulation.source.correlated_gamma.probability == 0.582
        # Placement stays exactly as written in the simulation config.
        assert simulation.source.gps.position.center_mm.z_mm == -100.0
        assert simulation.source.gps.position.radius_mm == 10.0

    def test_inline_fields_override_catalog(self, tmp_path):
        """Inline particle/energy/angular win over the catalog entry."""
        yaml_file = tmp_path / "ambe_override.yaml"
        yaml_file.write_text(
            """
source:
  catalogId: AmBe
  gps:
    particle: gamma
    position:
      centerMm: {x_mm: 0.0, y_mm: 0.0, z_mm: -100.0}
      radiusMm: 10.0
    energy:
      type: Mono
      monoMeV: 4.439
"""
            + self._scintillator_and_metadata_block()
        )

        simulation = from_yaml(yaml_file)

        # Inline particle and energy are kept; angular still comes from the catalog.
        assert simulation.source.gps.particle == "gamma"
        assert simulation.source.gps.energy.type == "Mono"
        assert simulation.source.gps.energy.mono_mev == 4.439
        assert simulation.source.gps.angular.type == "iso"

    def test_no_hydration_when_disabled(self, tmp_path):
        """With hydration off, an un-filled catalog source keeps None fields."""
        yaml_file = tmp_path / "ambe_no_hydrate.yaml"
        yaml_file.write_text(
            """
source:
  catalogId: AmBe
  gps:
    position:
      centerMm: {x_mm: 0.0, y_mm: 0.0, z_mm: -100.0}
      radiusMm: 10.0
"""
            + self._scintillator_and_metadata_block()
        )

        simulation = from_yaml(yaml_file, hydrate_catalogs=False)

        assert simulation.source.catalog_id == "AmBe"
        assert simulation.source.gps.particle is None
        assert simulation.source.gps.energy is None

    def test_hydrated_source_writes_ambe_macro(self, tmp_path):
        """A hydrated AmBe source should drive the arbitrary-energy macro output."""
        from src.config.macro import write_macro

        yaml_file = tmp_path / "ambe_macro.yaml"
        yaml_file.write_text(
            f"""
source:
  catalogId: AmBe
  gps:
    position:
      centerMm: {{x_mm: 0.0, y_mm: 0.0, z_mm: -100.0}}
      radiusMm: 10.0

optical:
  lenses:
    - {{name: TestLens, primary: true, zmxFile: test.zmx}}
  interface:
    diameterMm: 60.55
    positionMm: {{x_mm: 0.0, y_mm: 0.0, z_mm: 210.05}}

scintillator:
  position_mm: {{x_mm: 0.0, y_mm: 0.0, z_mm: 0.0}}
  dimension_mm: {{x_mm: 100.0, y_mm: 100.0, z_mm: 20.0}}
  properties:
    name: TestScint
    composition:
      density: 1.023
      elements:
        - {{symbol: C, massFraction: 0.914706}}
        - {{symbol: H, massFraction: 0.085294}}
    optical:
      photonEnergy: [2.0, 3.0, 4.0]
      rIndex: [1.58, 1.58, 1.58]
      nKEntries: 3
      timeComponents:
        default:
          - {{timeConstant: 2.4, yieldFraction: 1.0}}
          - {{timeConstant: 0.0, yieldFraction: 0.0}}
          - {{timeConstant: 0.0, yieldFraction: 0.0}}

geant4runner:
  numberOfParticles: 100
  binary: scintipix

metadata:
  author: Test Author
  date: "2026-06-16"
  version: v1.0
  description: Test configuration
  RunEnvironment:
    SimulationRunID: test_run
    WorkingDirectory: {tmp_path}
    MacroDirectory: macros
    LogDirectory: logs
"""
        )

        simulation = from_yaml(yaml_file)
        macro_path = write_macro(simulation)
        commands = macro_path.read_text(encoding="utf-8").strip().split("\n")

        assert "/gps/particle neutron" in commands
        assert "/gps/ene/type Arb" in commands
        assert "/gps/hist/type arb" in commands
        assert "/gps/hist/inter Lin" in commands
        assert "/gps/ang/type iso" in commands
        # Geant4 resets the angular type to "planar" when /gps/direction is given,
        # which would turn this isotropic source into a straight beam.
        assert not any(cmd.startswith("/gps/direction") for cmd in commands)

        hist_points = [c for c in commands if c.startswith("/gps/hist/point ")]
        assert len(hist_points) == 240
        assert hist_points[0] == "/gps/hist/point 0.025 0.461933"
        assert hist_points[-1] == "/gps/hist/point 11.975 0"

        assert "/source/correlatedGamma/enabled 1" in commands
        assert "/source/correlatedGamma/probability 0.582" in commands
        assert not any(cmd.startswith("/gps/ene/mono") for cmd in commands)
