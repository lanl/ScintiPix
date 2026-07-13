"""Shared path utilities for configuration modules.

These helpers are intentionally dependency-light so models and configuration
loaders can share path behavior without circular imports.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

try:
    from pydantic import Field
    from src.models.base import StrictModel
except ModuleNotFoundError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from pydantic import Field
    from src.models.base import StrictModel


class ValueWithUnit(StrictModel):
    """A numeric value with an associated unit string.

    Used throughout models to make physical units explicit in both
    catalog files and simulation configurations. Provides type safety
    and enables automatic unit conversion.

    Examples:
        >>> density = ValueWithUnit(value=1.05, unit="g/cm3")
        >>> energy = ValueWithUnit(value=6.0, unit="MeV")
    """

    value: float
    unit: str = Field(min_length=1)

    def to_g_cm3(self) -> float:
        """Convert density to g/cm³."""
        return convert_density_to_g_cm3(self.value, self.unit)

    def to_ns(self) -> float:
        """Convert time to nanoseconds."""
        return convert_time_to_ns(self.value, self.unit)

    def to_mev(self) -> float:
        """Convert energy to MeV."""
        return convert_energy_to_mev(self.value, self.unit)

    def to_per_mev(self) -> float:
        """Convert scintillation yield to photons/MeV."""
        return convert_scint_yield_to_per_mev(self.value, self.unit)


def convert_density_to_g_cm3(value: float, unit: str) -> float:
    """Convert density value to g/cm³."""
    normalized_unit = unit.lower().replace(" ", "").replace("^", "")
    factor = _DENSITY_UNIT_TO_G_CM3.get(normalized_unit)
    if factor is None:
        raise ValueError(f"Unsupported density unit: {unit!r}")
    return value * factor


def convert_time_to_ns(value: float, unit: str) -> float:
    """Convert time value to nanoseconds."""
    normalized_unit = unit.lower().replace(" ", "")
    factor = _TIME_UNIT_TO_NS.get(normalized_unit)
    if factor is None:
        raise ValueError(f"Unsupported time unit: {unit!r}")
    return value * factor


def convert_energy_to_mev(value: float, unit: str) -> float:
    """Convert energy value to MeV."""
    normalized_unit = unit.lower().replace(" ", "")
    factor = _ENERGY_UNIT_TO_MEV.get(normalized_unit)
    if factor is None:
        raise ValueError(f"Unsupported energy unit: {unit!r}")
    return value * factor


def convert_scint_yield_to_per_mev(value: float, unit: str) -> float:
    """Convert scintillation yield to photons/MeV."""
    normalized_unit = unit.lower().replace(" ", "")
    factor = _SCINT_YIELD_UNIT_TO_PER_MEV.get(normalized_unit)
    if factor is None:
        raise ValueError(f"Unsupported scintillation yield unit: {unit!r}")
    return value * factor


def extract_numeric_value(
    value_or_unit: "ValueWithUnit | float",
    *,
    converter: callable | None = None,
) -> float:
    """Extract numeric value from ValueWithUnit or float.

    Args:
        value_or_unit: Either a ValueWithUnit or plain float
        converter: Optional conversion function (value, unit) -> converted_value

    Returns:
        Numeric value, converted if converter is provided

    Examples:
        >>> extract_numeric_value(5.0)
        5.0
        >>> extract_numeric_value(ValueWithUnit(value=1.0, unit="g/cm3"),
        ...                       converter=convert_density_to_g_cm3)
        1.0
    """
    if isinstance(value_or_unit, ValueWithUnit):
        if converter:
            return converter(value_or_unit.value, value_or_unit.unit)
        return value_or_unit.value
    return value_or_unit

_LENGTH_UNIT_TO_MM: dict[str, float] = {
    "nm": 1.0e-6,
    "nanometer": 1.0e-6,
    "nanometers": 1.0e-6,
    "um": 1.0e-3,
    "micrometer": 1.0e-3,
    "micrometers": 1.0e-3,
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "centimeters": 10.0,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
}

_ENERGY_UNIT_TO_MEV: dict[str, float] = {
    "ev": 1.0e-6,
    "kev": 1.0e-3,
    "mev": 1.0,
    "gev": 1.0e3,
}

_ENERGY_UNIT_TO_EV: dict[str, float] = {
    "ev": 1.0,
    "kev": 1.0e3,
    "mev": 1.0e6,
    "gev": 1.0e9,
}

_TIME_UNIT_TO_NS: dict[str, float] = {
    "s": 1.0e9,
    "ms": 1.0e6,
    "us": 1.0e3,
    "ns": 1.0,
    "ps": 1.0e-3,
}

_DENSITY_UNIT_TO_G_CM3: dict[str, float] = {
    "g/cm3": 1.0,
    "g/cm^3": 1.0,
    "kg/m3": 1.0e-3,
    "kg/m^3": 1.0e-3,
}

_SCINT_YIELD_UNIT_TO_PER_MEV: dict[str, float] = {
    "1/mev": 1.0,
    "1/kev": 1.0e3,
    "1/gev": 1.0e-3,
}


def _length_to_mm(value: float, unit: str) -> float:
    """Convert Geant4-style length value/unit tokens to millimeters."""

    factor = _LENGTH_UNIT_TO_MM.get(unit.strip().lower())
    if factor is None:
        raise ValueError(f"Unsupported length unit '{unit}'.")
    return value * factor


def _parse_length_tokens(tokens: list[str], command: str) -> float:
    """Parse macro tokenized length command payload and return millimeters."""

    if len(tokens) < 3:
        raise ValueError(
            f"Command '{command}' requires '<value> <unit>' tokens, got: {tokens!r}"
        )

    try:
        value = float(tokens[1])
    except ValueError as exc:
        raise ValueError(
            f"Command '{command}' has non-numeric value token: {tokens[1]!r}"
        ) from exc

    return _length_to_mm(value, tokens[2])


def _parse_vector3(tokens: list[str], command: str) -> tuple[float, float, float]:
    """Parse three scalar tokens from a macro command."""

    if len(tokens) < 4:
        raise ValueError(
            f"Command '{command}' requires three scalar tokens, got: {tokens!r}"
        )
    try:
        return float(tokens[1]), float(tokens[2]), float(tokens[3])
    except ValueError as exc:
        raise ValueError(
            f"Command '{command}' requires numeric vector tokens, got: {tokens[1:4]!r}"
        ) from exc


def _parse_energy_to_mev(tokens: list[str], command: str) -> float:
    """Parse `<value> <unit>` energy tokens and convert to MeV."""

    if len(tokens) < 3:
        raise ValueError(
            f"Command '{command}' requires '<value> <unit>' tokens, got: {tokens!r}"
        )
    try:
        value = float(tokens[1])
    except ValueError as exc:
        raise ValueError(
            f"Command '{command}' has non-numeric value token: {tokens[1]!r}"
        ) from exc
    factor = _ENERGY_UNIT_TO_MEV.get(tokens[2].strip().lower())
    if factor is None:
        raise ValueError(
            f"Command '{command}' has unsupported energy unit: {tokens[2]!r}."
        )
    return value * factor


def _parse_numeric_list_with_optional_unit(
    tokens: list[str],
    command: str,
) -> tuple[list[float], str | None]:
    """Parse list command payload into numeric values plus optional unit token."""

    if len(tokens) < 2:
        raise ValueError(
            f"Command '{command}' requires a numeric list payload, got: {tokens!r}"
        )

    unit: str | None = None
    payload_tokens = tokens[1:]
    if len(payload_tokens) >= 2:
        try:
            float(payload_tokens[-1])
        except ValueError:
            unit = payload_tokens[-1]
            payload_tokens = payload_tokens[:-1]

    if not payload_tokens:
        raise ValueError(f"Command '{command}' is missing numeric list values.")

    raw_payload = " ".join(payload_tokens).replace(",", " ")
    values: list[float] = []
    for piece in raw_payload.split():
        try:
            values.append(float(piece))
        except ValueError as exc:
            raise ValueError(
                f"Command '{command}' has non-numeric list token: {piece!r}"
            ) from exc

    if not values:
        raise ValueError(f"Command '{command}' is missing numeric list values.")

    return values, unit


def _parse_time_to_ns(tokens: list[str], command: str) -> float:
    """Parse `<value> <unit>` time tokens and convert to nanoseconds."""

    if len(tokens) < 3:
        raise ValueError(
            f"Command '{command}' requires '<value> <unit>' tokens, got: {tokens!r}"
        )
    try:
        value = float(tokens[1])
    except ValueError as exc:
        raise ValueError(
            f"Command '{command}' has non-numeric value token: {tokens[1]!r}"
        ) from exc
    factor = _TIME_UNIT_TO_NS.get(tokens[2].strip().lower())
    if factor is None:
        raise ValueError(
            f"Command '{command}' has unsupported time unit: {tokens[2]!r}."
        )
    return value * factor


def _parse_density_to_g_cm3(tokens: list[str], command: str) -> float:
    """Parse `<value> <unit>` density tokens and convert to g/cm3."""

    if len(tokens) < 3:
        raise ValueError(
            f"Command '{command}' requires '<value> <unit>' tokens, got: {tokens!r}"
        )
    try:
        value = float(tokens[1])
    except ValueError as exc:
        raise ValueError(
            f"Command '{command}' has non-numeric value token: {tokens[1]!r}"
        ) from exc
    factor = _DENSITY_UNIT_TO_G_CM3.get(tokens[2].strip().lower())
    if factor is None:
        raise ValueError(
            f"Command '{command}' has unsupported density unit: {tokens[2]!r}."
        )
    return value * factor


def _parse_scint_yield_to_per_mev(tokens: list[str], command: str) -> float:
    """Parse scintillation-yield command payload into photons/MeV."""

    if len(tokens) < 2:
        raise ValueError(
            f"Command '{command}' requires at least a value token, got: {tokens!r}"
        )
    try:
        value = float(tokens[1])
    except ValueError as exc:
        raise ValueError(
            f"Command '{command}' has non-numeric value token: {tokens[1]!r}"
        ) from exc

    if len(tokens) == 2:
        return value

    factor = _SCINT_YIELD_UNIT_TO_PER_MEV.get(tokens[2].strip().lower())
    if factor is None:
        raise ValueError(
            f"Command '{command}' has unsupported scintillation-yield unit: {tokens[2]!r}."
        )
    return value * factor


def repo_root() -> Path:
    """Return repository root inferred from this module location."""

    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path, *, base_directory: str | Path | None = None) -> Path:
    """Resolve a path to an absolute path.

    Behavior:
    - Expands `~`.
    - Absolute inputs are returned as-is (resolved).
    - Relative inputs are resolved against `base_directory` when provided,
      otherwise against repository root.
    """

    resolved = Path(path).expanduser()
    if resolved.is_absolute():
        return resolved.resolve()

    if base_directory is None:
        base = repo_root()
    else:
        base = Path(base_directory).expanduser()
        if not base.is_absolute():
            base = repo_root() / base
        base = base.resolve()

    return (base / resolved).resolve()


def resolve_optional_path(
    value: Any,
    *,
    key_name: str,
    base_directory: str | Path | None = None,
) -> Path | None:
    """Resolve an optional YAML path-like value into an absolute path.

    Validation behavior:
    - `None` or blank string -> `None`
    - non-string non-null -> `ValueError`
    - relative string -> resolved against `base_directory` (or repo root)
    """

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"YAML key `{key_name}` must be a string when provided.")
    if not value.strip():
        return None
    return resolve_path(value, base_directory=base_directory)


def ensure_directory(
    path: str | Path,
    *,
    create: bool = False,
    label: str = "directory",
) -> Path:
    """Ensure a path resolves to an existing directory and return it.

    Parameters
    ----------
    path:
        Path-like directory target.
    create:
        When ``True``, create missing directories recursively.
    label:
        Context label used in raised error messages.
    """

    directory = Path(path).expanduser().resolve()

    if directory.exists():
        if not directory.is_dir():
            raise NotADirectoryError(f"{label} is not a directory: {directory}")
        return directory

    if not create:
        raise FileNotFoundError(f"{label} does not exist: {directory}")

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_directories(
    paths: dict[str, str | Path],
    *,
    create: bool = False,
) -> dict[str, Path]:
    """Ensure a labeled set of paths are directories and return resolved paths."""

    return {
        label: ensure_directory(path, create=create, label=label)
        for label, path in paths.items()
    }


def assert_directory_writable(
    path: str | Path,
    *,
    label: str = "directory",
) -> None:
    """Raise if directory is not writable by the current process."""

    directory = ensure_directory(path, create=False, label=label)
    try:
        with tempfile.NamedTemporaryFile(dir=directory):
            pass
    except OSError as exc:
        raise PermissionError(f"{label} is not writable: {directory}") from exc


def assert_distinct_paths(paths: dict[str, str | Path]) -> None:
    """Raise if any provided path labels resolve to the same directory."""

    seen: dict[Path, str] = {}
    for label, raw_path in paths.items():
        resolved = Path(raw_path).expanduser().resolve()
        existing_label = seen.get(resolved)
        if existing_label is not None:
            raise ValueError(
                "Directory collision detected: "
                f"{label} and {existing_label} both resolve to {resolved}"
            )
        seen[resolved] = label
