"""Run the existing API from the repository root after pip install -e ."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("aura.api:app", host="127.0.0.1", port=8000)
