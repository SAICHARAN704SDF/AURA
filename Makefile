install:
	python3 -m pip install -e '.[test]'
test:
	python3 -m pytest -q
	node frontend/tests/test_workflow_canvas.cjs
	node frontend/tests/test_subject_workflows.cjs
	node frontend/tests/test_replay.cjs
verify:
	PYTHONPATH=backend/src python3 backend/scripts/verify_models.py
serve:
	PYTHONPATH=backend/src python3 -m uvicorn aura.api:app --host 127.0.0.1 --port 8000
graph:
	PYTHONPATH=backend/src python backend/scripts/show_graph.py
