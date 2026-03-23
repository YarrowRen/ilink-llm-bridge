import logging
import sys

_LOG_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warn": logging.WARNING, "error": logging.ERROR}

logging.basicConfig(
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger("bridge")
logger.setLevel(logging.INFO)


def set_log_level(level: str) -> None:
    logger.setLevel(_LOG_LEVELS.get(level.lower(), logging.INFO))
