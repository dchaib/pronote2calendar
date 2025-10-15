import logging
import os
import sys
from typing import Optional


def setup_logging(config_level: Optional[str] = None) -> None:
    chosen = config_level or os.getenv("LOG_LEVEL") or "INFO"
    level = getattr(logging, chosen.upper(), logging.INFO)

    root = logging.getLogger()
    # Clear existing handlers to avoid duplicate logs when reloading
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    formatter = logging.Formatter(fmt, "%Y-%m-%dT%H:%M:%S%z")
    handler.setFormatter(formatter)

    root.setLevel(level)
    root.addHandler(handler)
