"""Comprehensive unit tests for Geant4 runtime configuration models."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from pydantic import ValidationError


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "src").is_dir() and (parent / "pixi.toml").is_file():
            return parent
    raise RuntimeError("Could not resolve repository root from test path.")


sys.path.insert(0, str(_repo_root()))

from src.models.geant4runtime import (
    Geant4OutputConfig,
    Geant4RunTime,
    Geant4RuntimeControls,
)


# ============================================================================
# Geant4RuntimeControls Tests
# ============================================================================


class TestGeant4RuntimeControls:
    """Tests for Geant4 macro preamble controls."""

    def test_all_fields_default_to_none(self) -> None:
        """All control fields should default to None, but at least one is required."""
        # Cannot create with all None - requires at least one control
        with pytest.raises(
            ValidationError,
            match="must set at least one control value",
        ):
            Geant4RuntimeControls()

    def test_control_verbose_only(self) -> None:
        """Setting only control_verbose should validate."""
        controls = Geant4RuntimeControls(control_verbose=1)
        assert controls.control_verbose == 1
        assert controls.run_verbose is None
        assert controls.event_verbose is None
        assert controls.tracking_verbose is None
        assert controls.print_progress is None
        assert controls.store_trajectory is None

    def test_run_verbose_only(self) -> None:
        """Setting only run_verbose should validate."""
        controls = Geant4RuntimeControls(run_verbose=2)
        assert controls.run_verbose == 2
        assert controls.control_verbose is None

    def test_event_verbose_only(self) -> None:
        """Setting only event_verbose should validate."""
        controls = Geant4RuntimeControls(event_verbose=0)
        assert controls.event_verbose == 0

    def test_tracking_verbose_only(self) -> None:
        """Setting only tracking_verbose should validate."""
        controls = Geant4RuntimeControls(tracking_verbose=3)
        assert controls.tracking_verbose == 3

    def test_print_progress_only(self) -> None:
        """Setting only print_progress should validate."""
        controls = Geant4RuntimeControls(print_progress=100)
        assert controls.print_progress == 100

    def test_store_trajectory_only(self) -> None:
        """Setting only store_trajectory should validate."""
        controls = Geant4RuntimeControls(store_trajectory=True)
        assert controls.store_trajectory is True

    def test_control_verbose_alias_handling(self) -> None:
        """camelCase controlVerbose alias should map to control_verbose."""
        controls = Geant4RuntimeControls.model_validate({"controlVerbose": 1})
        assert controls.control_verbose == 1

    def test_run_verbose_alias_handling(self) -> None:
        """camelCase runVerbose alias should map to run_verbose."""
        controls = Geant4RuntimeControls.model_validate({"runVerbose": 2})
        assert controls.run_verbose == 2

    def test_event_verbose_alias_handling(self) -> None:
        """camelCase eventVerbose alias should map to event_verbose."""
        controls = Geant4RuntimeControls.model_validate({"eventVerbose": 3})
        assert controls.event_verbose == 3

    def test_tracking_verbose_alias_handling(self) -> None:
        """camelCase trackingVerbose alias should map to tracking_verbose."""
        controls = Geant4RuntimeControls.model_validate({"trackingVerbose": 4})
        assert controls.tracking_verbose == 4

    def test_print_progress_alias_handling(self) -> None:
        """camelCase printProgress alias should map to print_progress."""
        controls = Geant4RuntimeControls.model_validate({"printProgress": 50})
        assert controls.print_progress == 50

    def test_store_trajectory_alias_handling(self) -> None:
        """camelCase storeTrajectory alias should map to store_trajectory."""
        controls = Geant4RuntimeControls.model_validate({"storeTrajectory": False})
        assert controls.store_trajectory is False

    def test_multiple_controls_set(self) -> None:
        """Multiple controls can be set simultaneously."""
        controls = Geant4RuntimeControls(
            control_verbose=1,
            run_verbose=2,
            event_verbose=0,
            tracking_verbose=3,
            print_progress=100,
            store_trajectory=True,
        )
        assert controls.control_verbose == 1
        assert controls.run_verbose == 2
        assert controls.event_verbose == 0
        assert controls.tracking_verbose == 3
        assert controls.print_progress == 100
        assert controls.store_trajectory is True

    def test_verbose_levels_non_negative(self) -> None:
        """Verbose levels must be non-negative (ge=0)."""
        controls = Geant4RuntimeControls(control_verbose=0)
        assert controls.control_verbose == 0

        with pytest.raises(ValidationError, match="control_verbose"):
            Geant4RuntimeControls(control_verbose=-1)

        with pytest.raises(ValidationError, match="run_verbose"):
            Geant4RuntimeControls(run_verbose=-1)

        with pytest.raises(ValidationError, match="event_verbose"):
            Geant4RuntimeControls(event_verbose=-1)

        with pytest.raises(ValidationError, match="tracking_verbose"):
            Geant4RuntimeControls(tracking_verbose=-1)

    def test_print_progress_positive(self) -> None:
        """print_progress must be positive (gt=0)."""
        controls = Geant4RuntimeControls(print_progress=1)
        assert controls.print_progress == 1

        with pytest.raises(ValidationError, match="print_progress"):
            Geant4RuntimeControls(print_progress=0)

        with pytest.raises(ValidationError, match="print_progress"):
            Geant4RuntimeControls(print_progress=-10)

    def test_store_trajectory_boolean_values(self) -> None:
        """store_trajectory should accept boolean values."""
        controls_true = Geant4RuntimeControls(store_trajectory=True)
        assert controls_true.store_trajectory is True

        controls_false = Geant4RuntimeControls(store_trajectory=False)
        assert controls_false.store_trajectory is False

    def test_empty_controls_rejected(self) -> None:
        """Empty controls block with all None should be rejected."""
        with pytest.raises(
            ValidationError,
            match="must set at least one control value",
        ):
            Geant4RuntimeControls()

    def test_explicit_none_values_rejected(self) -> None:
        """Explicitly setting all fields to None should be rejected."""
        with pytest.raises(
            ValidationError,
            match="must set at least one control value",
        ):
            Geant4RuntimeControls(
                control_verbose=None,
                run_verbose=None,
                event_verbose=None,
                tracking_verbose=None,
                print_progress=None,
                store_trajectory=None,
            )

    def test_high_verbose_levels_accepted(self) -> None:
        """High verbose levels should be accepted."""
        controls = Geant4RuntimeControls(
            control_verbose=10,
            run_verbose=100,
            event_verbose=5,
            tracking_verbose=20,
        )
        assert controls.control_verbose == 10
        assert controls.run_verbose == 100


# ============================================================================
# Geant4RunTime Tests
# ============================================================================


class TestGeant4RunTime:
    """Tests for Geant4 run-command settings."""

    def test_valid_with_number_of_particles_only(self) -> None:
        """Valid runtime with only number_of_particles should validate."""
        runtime = Geant4RunTime(number_of_particles=1000)
        assert runtime.number_of_particles == 1000
        assert runtime.runtime_controls is None
        assert runtime.binary == "scintipix"
        assert runtime.show_progress is False
        assert runtime.verify_output is True

    def test_valid_with_runtime_controls_only(self) -> None:
        """Valid runtime with only runtime_controls should validate."""
        runtime = Geant4RunTime(
            runtime_controls={"controlVerbose": 1},
        )
        assert runtime.number_of_particles is None
        assert runtime.runtime_controls.control_verbose == 1

    def test_valid_with_both_fields(self) -> None:
        """Valid runtime with both number_of_particles and runtime_controls should validate."""
        runtime = Geant4RunTime(
            number_of_particles=5000,
            runtime_controls={"runVerbose": 2},
        )
        assert runtime.number_of_particles == 5000
        assert runtime.runtime_controls.run_verbose == 2

    def test_number_of_particles_alias_handling(self) -> None:
        """camelCase numberOfParticles alias should map to number_of_particles."""
        runtime = Geant4RunTime.model_validate({"numberOfParticles": 2000})
        assert runtime.number_of_particles == 2000

    def test_runtime_controls_alias_handling(self) -> None:
        """camelCase runtimeControls alias should map to runtime_controls."""
        runtime = Geant4RunTime.model_validate(
            {
                "numberOfParticles": 1000,
                "runtimeControls": {"controlVerbose": 1},
            }
        )
        assert runtime.runtime_controls.control_verbose == 1

    def test_binary_default(self) -> None:
        """binary should default to 'scintipix'."""
        runtime = Geant4RunTime(number_of_particles=1000)
        assert runtime.binary == "scintipix"

    def test_events_per_output_alias_handling(self) -> None:
        """camelCase eventsPerOutput alias should map to events_per_output."""
        runtime = Geant4RunTime.model_validate(
            {
                "numberOfParticles": 1000,
                "eventsPerOutput": 25,
            }
        )
        assert runtime.events_per_output == 25

    def test_events_per_output_default(self) -> None:
        """events_per_output should default to 1000."""
        runtime = Geant4RunTime(number_of_particles=1000)
        assert runtime.events_per_output == 1000

    def test_events_per_output_positive(self) -> None:
        """events_per_output must be positive."""
        runtime = Geant4RunTime(number_of_particles=1000, events_per_output=1)
        assert runtime.events_per_output == 1

        with pytest.raises(ValidationError, match="events_per_output"):
            Geant4RunTime(number_of_particles=1000, events_per_output=0)

        with pytest.raises(ValidationError, match="events_per_output"):
            Geant4RunTime(number_of_particles=1000, events_per_output=-1)

    def test_output_defaults_enable_all_tables(self) -> None:
        """All Geant4 output tables should be enabled by default."""
        runtime = Geant4RunTime(number_of_particles=1000)
        assert runtime.output.primaries is True
        assert runtime.output.secondaries is True
        assert runtime.output.photons is True

    def test_output_block_accepts_selected_tables(self) -> None:
        """The output block should control individual output tables."""
        runtime = Geant4RunTime.model_validate(
            {
                "numberOfParticles": 1000,
                "output": {
                    "primaries": True,
                    "secondaries": False,
                    "photons": False,
                },
            }
        )
        assert runtime.output.primaries is True
        assert runtime.output.secondaries is False
        assert runtime.output.photons is False

    def test_output_block_rejects_all_disabled_tables(self) -> None:
        """At least one output table must remain enabled."""
        with pytest.raises(
            ValidationError,
            match="must enable at least one table",
        ):
            Geant4OutputConfig(primaries=False, secondaries=False, photons=False)

        with pytest.raises(
            ValidationError,
            match="must enable at least one table",
        ):
            Geant4RunTime.model_validate(
                {
                    "numberOfParticles": 1000,
                    "output": {
                        "primaries": False,
                        "secondaries": False,
                        "photons": False,
                    },
                }
            )

    def test_binary_custom_value(self) -> None:
        """Custom binary name should be accepted."""
        runtime = Geant4RunTime(
            number_of_particles=1000,
            binary="custom_geant4",
        )
        assert runtime.binary == "custom_geant4"

    def test_show_progress_alias_handling(self) -> None:
        """camelCase showProgress alias should map to show_progress."""
        runtime = Geant4RunTime.model_validate(
            {
                "numberOfParticles": 1000,
                "showProgress": True,
            }
        )
        assert runtime.show_progress is True

    def test_show_progress_default_false(self) -> None:
        """show_progress should default to False."""
        runtime = Geant4RunTime(number_of_particles=1000)
        assert runtime.show_progress is False

    def test_verify_output_alias_handling(self) -> None:
        """camelCase verifyOutput alias should map to verify_output."""
        runtime = Geant4RunTime.model_validate(
            {
                "numberOfParticles": 1000,
                "verifyOutput": False,
            }
        )
        assert runtime.verify_output is False

    def test_verify_output_default_true(self) -> None:
        """verify_output should default to True."""
        runtime = Geant4RunTime(number_of_particles=1000)
        assert runtime.verify_output is True

    def test_number_of_particles_positive(self) -> None:
        """number_of_particles must be positive (gt=0)."""
        runtime = Geant4RunTime(number_of_particles=1)
        assert runtime.number_of_particles == 1

        with pytest.raises(ValidationError, match="number_of_particles"):
            Geant4RunTime(number_of_particles=0)

        with pytest.raises(ValidationError, match="number_of_particles"):
            Geant4RunTime(number_of_particles=-100)

    def test_large_number_of_particles_accepted(self) -> None:
        """Large number_of_particles values should be accepted."""
        runtime = Geant4RunTime(number_of_particles=1000000)
        assert runtime.number_of_particles == 1000000

    def test_empty_binary_rejected(self) -> None:
        """Empty binary string should be rejected (min_length=1)."""
        with pytest.raises(ValidationError, match="binary"):
            Geant4RunTime(
                number_of_particles=1000,
                binary="",
            )

    def test_whitespace_binary_rejected(self) -> None:
        """Whitespace-only binary should be rejected."""
        with pytest.raises(ValidationError, match="must not be blank"):
            Geant4RunTime(
                number_of_particles=1000,
                binary="   ",
            )

    def test_binary_with_path(self) -> None:
        """binary with path should be accepted."""
        runtime = Geant4RunTime(
            number_of_particles=1000,
            binary="/usr/local/bin/geant4_app",
        )
        assert runtime.binary == "/usr/local/bin/geant4_app"

    def test_binary_whitespace_trimmed(self) -> None:
        """binary with surrounding whitespace should be trimmed."""
        runtime = Geant4RunTime(
            number_of_particles=1000,
            binary="  geant4  ",
        )
        assert runtime.binary == "geant4"

    def test_missing_both_fields_rejected(self) -> None:
        """Runtime without number_of_particles or runtime_controls should be rejected."""
        with pytest.raises(
            ValidationError,
            match="must include `numberOfParticles` and/or `runtimeControls`",
        ):
            Geant4RunTime()

    def test_explicit_none_for_both_fields_rejected(self) -> None:
        """Explicitly setting both required fields to None should be rejected."""
        with pytest.raises(
            ValidationError,
            match="must include `numberOfParticles` and/or `runtimeControls`",
        ):
            Geant4RunTime(
                number_of_particles=None,
                runtime_controls=None,
            )

    def test_complete_configuration(self) -> None:
        """Complete configuration with all fields should validate."""
        runtime = Geant4RunTime(
            number_of_particles=10000,
            runtime_controls={
                "controlVerbose": 1,
                "runVerbose": 2,
                "eventVerbose": 0,
                "trackingVerbose": 3,
                "printProgress": 1000,
                "storeTrajectory": True,
            },
            binary="custom_geant4_binary",
            events_per_output=250,
            show_progress=True,
            verify_output=False,
        )
        assert runtime.number_of_particles == 10000
        assert runtime.runtime_controls.control_verbose == 1
        assert runtime.runtime_controls.run_verbose == 2
        assert runtime.runtime_controls.print_progress == 1000
        assert runtime.runtime_controls.store_trajectory is True
        assert runtime.binary == "custom_geant4_binary"
        assert runtime.events_per_output == 250
        assert runtime.show_progress is True
        assert runtime.verify_output is False

    def test_minimal_with_number_of_particles(self) -> None:
        """Minimal configuration with just number_of_particles should use defaults."""
        runtime = Geant4RunTime.model_validate({"numberOfParticles": 100})
        assert runtime.number_of_particles == 100
        assert runtime.runtime_controls is None
        assert runtime.binary == "scintipix"
        assert runtime.show_progress is False
        assert runtime.verify_output is True

    def test_minimal_with_runtime_controls(self) -> None:
        """Minimal configuration with just runtime_controls should use defaults."""
        runtime = Geant4RunTime.model_validate(
            {
                "runtimeControls": {"printProgress": 50},
            }
        )
        assert runtime.number_of_particles is None
        assert runtime.runtime_controls.print_progress == 50
        assert runtime.binary == "scintipix"
        assert runtime.show_progress is False
        assert runtime.verify_output is True

    def test_serialization_uses_aliases(self) -> None:
        """Serialized output should use camelCase aliases."""
        runtime = Geant4RunTime(
            number_of_particles=1000,
            runtime_controls={"controlVerbose": 1},
            show_progress=True,
            verify_output=False,
        )
        dumped = runtime.model_dump(by_alias=True)
        assert "numberOfParticles" in dumped
        assert "runtimeControls" in dumped
        assert "eventsPerOutput" in dumped
        assert "output" in dumped
        assert "showProgress" in dumped
        assert "verifyOutput" in dumped

    def test_nested_runtime_controls_validation(self) -> None:
        """Nested runtime_controls should validate properly."""
        # Valid nested controls
        runtime = Geant4RunTime(
            number_of_particles=1000,
            runtime_controls={"runVerbose": 1, "eventVerbose": 2},
        )
        assert runtime.runtime_controls.run_verbose == 1
        assert runtime.runtime_controls.event_verbose == 2

        # Invalid nested controls (empty)
        with pytest.raises(
            ValidationError,
            match="must set at least one control value",
        ):
            Geant4RunTime(
                number_of_particles=1000,
                runtime_controls={},
            )

    def test_runtime_controls_with_negative_print_progress_rejected(self) -> None:
        """runtime_controls with invalid print_progress should be rejected."""
        with pytest.raises(ValidationError, match="greater than 0"):
            Geant4RunTime(
                number_of_particles=1000,
                runtime_controls={"printProgress": 0},
            )
