"""Simple logging utilities.

This module provides a no‑op logger for the toy model. In future
versions this can be replaced with more sophisticated logging and
configurable verbosity.
"""

import logging

logger = logging.getLogger("agent_zero")


def configure_logging(level: int = logging.INFO) -> None:
    """Configure basic logging for the package."""
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
