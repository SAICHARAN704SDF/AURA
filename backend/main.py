"""
FILE: backend/main.py
PURPOSE: Start the standalone local API and dashboard.
MAIN RESPONSIBILITY: Local entry point.
INPUTS: Environment configuration through aura.api startup.
OUTPUTS: Uvicorn server on localhost:8000.
IMPORTANT FUNCTIONS: __main__ entry block.
CONNECTED MODULES: uvicorn, aura.api.application
WHERE THIS FILE IS USED: Manual startup/setup from the repository root.
PRESENTATION EXPLANATION: "This entry point starts our existing application; services are wired in create_app."
"""
# PRESENTATION SECTION: SERVER ENTRY POINT
import uvicorn

if __name__ == "__main__":
    uvicorn.run("aura.api:app", host="127.0.0.1", port=8000)
