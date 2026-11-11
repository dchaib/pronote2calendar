import logging
import os
import sys

LOG_LEVELS = {
    name: getattr(logging, name)
    for name in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
}


def normalize_log_level(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Log level must be a string")
    level = value.strip().upper()
    if level not in LOG_LEVELS:
        raise ValueError(
            f"Invalid log level {value!r}; expected one of {', '.join(LOG_LEVELS)}"
        )
    return level


def setup_logging(
    config_level: str = "INFO",
    *,
    use_environment: bool = True,
) -> None:
    chosen = os.getenv("LOG_LEVEL", config_level) if use_environment else config_level
    level = LOG_LEVELS[normalize_log_level(chosen)]

    root = logging.getLogger()
    # Replace only our handler; preserve handlers owned by an embedding application.
    for handler in list(root.handlers):
        if handler.name == "pronote2calendar":
            root.removeHandler(handler)
            handler.close()

    handler = logging.StreamHandler(sys.stdout)
    handler.name = "pronote2calendar"
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%dT%H:%M:%S%z"
        )
    )
    root.setLevel(logging.WARNING)
    logging.getLogger("pronote2calendar").setLevel(level)
    root.addHandler(handler)
