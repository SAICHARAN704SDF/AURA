test:
	python3 -m pytest -q
verify:
	PYTHONPATH=src python3 scripts/verify_models.py
serve:
	PYTHONPATH=src python3 -m uvicorn aura.api:app --host 127.0.0.1 --port 8000
