"""
FILE: backend/src/aura/core/logging_config.py
PURPOSE: Configure application logging and suppress noisy HTTP logs.
MAIN RESPONSIBILITY: Logging Policy.
INPUTS: Logging configuration call at startup.
OUTPUTS: Configured Python logging.
IMPORTANT FUNCTIONS / CLASSES: configure_logging.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "Logging is kept separate from the workflow event viewer."
"""
# PRESENTATION SECTION: LOGGING POLICY
import logging
def configure_logging() -> None:
    import os
    logging.basicConfig(level=logging.WARNING)
    if os.environ.get('RESEARCHOS_JSON_LOGS') == '1':
        events = logging.getLogger('researchos.events')
        events.setLevel(logging.INFO)
        if not events.handlers:
            events.addHandler(logging.StreamHandler())
        events.propagate = False
    for name in ('httpx', 'httpcore'):
        logging.getLogger(name).setLevel(logging.CRITICAL)
