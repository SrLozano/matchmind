.PHONY: api-install api-dev api-test api-health

api-install:
	python -m pip install -r apps/api/requirements.txt

api-dev:
	cd apps/api && uvicorn app.main:app --reload

api-test:
	cd apps/api && python -m unittest discover tests

api-health:
	curl http://localhost:8000/health
