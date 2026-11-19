"""
FILE: backend/src/aura/core/exceptions.py
PURPOSE: Represent service failures with stable error codes.
MAIN RESPONSIBILITY: Safe Errors.
INPUTS: Error code string.
OUTPUTS: ServiceError for API and workflow error handling.
IMPORTANT FUNCTIONS / CLASSES: ServiceError.
CONNECTED MODULES: See imports below for local and external dependencies.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "We propagate an error code instead of raw provider responses that could reveal sensitive data."
"""
# PRESENTATION SECTION: SAFE ERRORS
class ServiceError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
