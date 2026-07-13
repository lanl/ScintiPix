"""Shared Python logging backed by Loguru."""

from __future__ import annotations

from contextlib import contextmanager
import re
import time


DEFAULT_RUN_LOG_FILENAME = "runLog.txt"
_SCREEN_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "{extra[stage_prefix]}{extra[message_body]}"
)
_STAGE_PREFIX_PATTERN = re.compile(
    r"^\[(setup|run|simulation|transport|intensifier|sensor)\]\s*"
)


def _require_loguru():
    """Import Loguru lazily with a project-specific install hint."""

    try:
        from loguru import logger
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "loguru is required for Python run logging. "
            "Install project dependencies with `pixi install`."
        ) from exc
    return logger


def _stage_prefix_patcher(record: dict[str, object]) -> None:
    """Expose colored stage prefixes without changing the message."""

    message = str(record["message"])
    match = _STAGE_PREFIX_PATTERN.match(message)
    if match is None:
        record["extra"]["stage_prefix"] = ""
        record["extra"]["message_body"] = message
        return
    record["extra"]["stage_prefix"] = f"<blue>[{match.group(1)}]</blue> "
    record["extra"]["message_body"] = message[match.end() :]


def get_logger():
    """Return the shared Loguru logger."""

    return _require_loguru().patch(_stage_prefix_patcher)


@contextmanager
def log_stage(stage_name: str):
    """Log a stage start/finish pair with elapsed wall time."""

    logger = get_logger()
    start_time = time.perf_counter()
    logger.info(f"[{stage_name}] Starting.")
    try:
        yield
    except Exception:
        elapsed_s = time.perf_counter() - start_time
        logger.exception(f"[{stage_name}] Failed after {elapsed_s:.2f} s.")
        raise
    elapsed_s = time.perf_counter() - start_time
    logger.info(f"[{stage_name}] Finished in {elapsed_s:.2f} s.")
