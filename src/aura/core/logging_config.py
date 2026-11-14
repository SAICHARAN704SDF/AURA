"""Suppress transport logs that may contain credentials."""
import logging
def configure_logging() -> None:
    logging.basicConfig(level=logging.WARNING)
    for name in ('httpx', 'httpcore'):
        logging.getLogger(name).setLevel(logging.CRITICAL)
