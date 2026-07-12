"""Unit tests for `src.runner.runSimulation`."""

from __future__ import annotations

import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, call, patch


def _repo_root() -> Path:
    """Resolve repository root by searching parent directories."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "src").is_dir() and (parent / "pixi.toml").is_file():
            return parent
    raise RuntimeError("Could not resolve repository root from test path.")


sys.path.insert(0, str(_repo_root()))


class RunSimulationTests(unittest.TestCase):
    """Validate runner launch behavior against resolved run artifacts."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.config.macro import write_macro
            from src.config.yaml import from_yaml
            from src.runner.runSimulation import run, run_simulation
            from src.runner.runSimulation import _parse_simulated_events
        except ModuleNotFoundError as exc:
            missing = (getattr(exc, "name", "") or "").lower()
            if missing in {"pydantic", "loguru"}:
                raise unittest.SkipTest(
                    f"Missing dependency for runner tests: {exc}. "
                    "Run in the project environment (for example: pixi run test-python)."
                ) from exc
            raise
        cls.from_yaml = staticmethod(from_yaml)
        cls.write_macro = staticmethod(write_macro)
        cls.parse_simulated_events = staticmethod(_parse_simulated_events)
        cls.runner_run = staticmethod(run)
        cls.run_simulation = staticmethod(run_simulation)

    class _FakeProcess:
        def __init__(self, lines: list[str], returncode: int = 0):
            self.stdout = io.StringIO("".join(lines))
            self.returncode = returncode

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.stdout.close()
            return False

        def wait(self) -> int:
            return self.returncode

    def _config_for_tmp(self, tmp_path: Path):
        config = self.from_yaml(
            _repo_root() / "examples" / "yamlFiles" / "CanonEF50mmf1p0L_example.yaml"
        )
        run_environment = config.metadata.run_environment
        run_environment.working_directory = tmp_path.as_posix()
        run_environment.simulation_run_id = "runner_test"
        run_environment.sub_run_number = 0
        run_environment.macro_directory = "macros"
        run_environment.log_directory = "logs"
        run_environment.primaries_directory = "primaries"
        run_environment.secondaries_directory = "secondaries"
        run_environment.simulated_photons_directory = "simulatedPhotons"
        run_environment.resolve_directories()
        run_environment.create_directories()
        return config

    def _macro_file(self, config) -> Path:
        env = config.metadata.run_environment
        return Path(env.macro_directory) / "runner_test_000.mac"

    def _log_file(self, config) -> Path:
        return Path(config.metadata.run_environment.log_directory) / "runLog.txt"

    def _primaries_output_file(self, config) -> Path:
        return (
            Path(config.metadata.run_environment.primaries_directory)
            / config.metadata.run_environment.primaries_filename
        )

    def _output_file(self, directory: str | Path, filename: str) -> Path:
        return Path(directory) / filename

    def _enabled_output_files(self, config) -> list[Path]:
        env = config.metadata.run_environment
        output = config.geant4runner.output
        files: list[Path] = []
        if output.primaries:
            files.append(
                self._output_file(
                    env.primaries_directory,
                    env.primaries_filename,
                )
            )
        if output.secondaries:
            files.append(
                self._output_file(
                    env.secondaries_directory,
                    env.secondaries_filename,
                )
            )
        if output.photons:
            files.append(
                self._output_file(
                    env.simulated_photons_directory,
                    env.photons_filename,
                )
            )
        return files

    def _write_enabled_outputs(self, config) -> None:
        for output_file in self._enabled_output_files(config):
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text("ok\n", encoding="utf-8")

    def test_parse_simulated_events_extracts_aggregate_count(self) -> None:
        self.assertEqual(
            self.parse_simulated_events("G4WT10 > Simulated 3000 events\n"),
            3000,
        )
        self.assertIsNone(
            self.parse_simulated_events(
                "G4WT9 > --> Event 6000 starts with initial seeds (1,2).\n"
            )
        )

    def test_run_dry_run_skips_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)

            with patch("src.runner.runSimulation.subprocess.Popen") as popen_mock:
                result = self.run_simulation(config, dry_run=True)

            self.assertIsNone(result)
            popen_mock.assert_not_called()
            self.assertTrue(self._macro_file(config).exists())

    def test_run_uses_binary_from_geant4runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)
            config.geant4runner.binary = "pixi run scintipix"
            self.write_macro(config)
            expected_log_path = self._log_file(config)
            self._write_enabled_outputs(config)

            with patch(
                "src.runner.runSimulation.subprocess.Popen",
                return_value=self._FakeProcess(
                    ["G4WT10 > Simulated 10000 events\n"],
                    returncode=0,
                ),
            ) as popen_mock, patch(
                "src.runner.runSimulation.sys.stderr",
                new=io.StringIO(),
            ):
                completed = self.run_simulation(config)

            self.assertIsInstance(completed, subprocess.CompletedProcess)
            popen_mock.assert_called_once_with(
                ["pixi", "run", "scintipix", str(self._macro_file(config).resolve())],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.assertIn(
                "Simulated 10000 events",
                expected_log_path.read_text(encoding="utf-8"),
            )

    def test_run_suppresses_terminal_progress_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)
            config.geant4runner.show_progress = False
            self.write_macro(config)
            self._write_enabled_outputs(config)

            with patch(
                "src.runner.runSimulation.subprocess.Popen",
                return_value=self._FakeProcess(
                    ["G4WT10 > Simulated 10000 events\n"],
                    returncode=0,
                ),
            ), patch(
                "src.runner.runSimulation.sys.stderr",
                new=io.StringIO(),
            ) as stderr_capture:
                self.run_simulation(config)

            self.assertNotIn("\rSimulation [", stderr_capture.getvalue())

    def test_run_rejects_missing_macro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)

            with patch("src.runner.runSimulation.subprocess.Popen") as popen_mock:
                with self.assertRaises(FileNotFoundError):
                    self.runner_run(config)

            popen_mock.assert_not_called()

    def test_run_requires_output_when_verification_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)
            self.write_macro(config)

            with patch(
                "src.runner.runSimulation.subprocess.Popen",
                return_value=self._FakeProcess(
                    ["G4WT10 > Simulated 10000 events\n"],
                    returncode=0,
                ),
            ) as popen_mock, patch(
                "src.runner.runSimulation.sys.stderr",
                new=io.StringIO(),
            ):
                with self.assertRaises(FileNotFoundError):
                    self.runner_run(config)

            popen_mock.assert_called_once()

    def test_run_skips_output_check_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)
            config.geant4runner.verify_output = False
            self.write_macro(config)

            with patch(
                "src.runner.runSimulation.subprocess.Popen",
                return_value=self._FakeProcess(
                    ["G4WT10 > Simulated 10000 events\n"],
                    returncode=0,
                ),
            ) as popen_mock, patch(
                "src.runner.runSimulation.sys.stderr",
                new=io.StringIO(),
            ):
                completed = self.runner_run(config)

            self.assertEqual(completed.returncode, 0)
            popen_mock.assert_called_once()

    def test_run_simulation_dry_run_writes_macro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)

            result = self.run_simulation(config, dry_run=True)

            self.assertIsNone(result)
            self.assertTrue(self._macro_file(config).exists())

    def test_run_simulation_uses_mutating_autofocus_contract(self) -> None:
        """Autofocus should mutate config before macro generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = self._config_for_tmp(Path(tmp_dir))
            config.metadata.run_controls.auto_focus_lens = True
            primary_lens = config.optical.lenses[0]
            primary_lens.focus_adjustment_mm = 1.0
            primary_lens.back_focus_mm = 40.0
            original_z_mm = config.optical.interface.position_mm.z_mm

            with patch(
                "src.runner.runSimulation.auto_focus_lens",
                side_effect=lambda focused_config: setattr(
                    focused_config.optical.interface.position_mm,
                    "z_mm",
                    321.0,
                ),
            ) as autofocus_mock, patch(
                "src.runner.runSimulation.write_macro",
            ) as write_macro_mock, patch(
                "src.runner.runSimulation.run",
                return_value=None,
            ) as run_mock:
                ordered_calls = Mock()
                ordered_calls.attach_mock(autofocus_mock, "autofocus")
                ordered_calls.attach_mock(write_macro_mock, "write_macro")

                result = self.run_simulation(config, dry_run=True)

            self.assertIsNone(result)
            self.assertEqual(
                ordered_calls.mock_calls[:2],
                [call.autofocus(config), call.write_macro(config)],
            )
            self.assertNotEqual(config.optical.interface.position_mm.z_mm, original_z_mm)
            self.assertEqual(config.optical.interface.position_mm.z_mm, 321.0)
            run_mock.assert_called_once_with(
                config,
                dry_run=True,
                log_filename=None,
            )

    def test_run_simulation_prepares_then_executes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)

            def _popen_side_effect(*args, **kwargs):
                self._write_enabled_outputs(config)
                return self._FakeProcess(
                    ["G4WT10 > Simulated 10000 events\n"],
                    returncode=0,
                )

            with patch(
                "src.runner.runSimulation.subprocess.Popen",
                side_effect=_popen_side_effect,
            ) as popen_mock, patch(
                "src.runner.runSimulation.sys.stderr",
                new=io.StringIO(),
            ):
                completed = self.run_simulation(config)

            self.assertEqual(completed.returncode, 0)
            self.assertTrue(self._macro_file(config).exists())
            popen_mock.assert_called_once()

    def test_run_verifies_only_enabled_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config = self._config_for_tmp(tmp_path)
            config.geant4runner.output.secondaries = False
            config.geant4runner.output.photons = False

            def _popen_side_effect(*args, **kwargs):
                self._primaries_output_file(config).parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                self._primaries_output_file(config).write_text(
                    "ok\n",
                    encoding="utf-8",
                )
                return self._FakeProcess(
                    ["G4WT10 > Simulated 10000 events\n"],
                    returncode=0,
                )

            with patch(
                "src.runner.runSimulation.subprocess.Popen",
                side_effect=_popen_side_effect,
            ), patch(
                "src.runner.runSimulation.sys.stderr",
                new=io.StringIO(),
            ):
                completed = self.run_simulation(config)

            self.assertEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
