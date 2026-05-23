PYTHON ?= $(shell if [ -x venv/bin/python ]; then printf 'venv/bin/python'; elif command -v python >/dev/null 2>&1; then printf 'python'; else printf 'python3'; fi)

.PHONY: api-install api-dev api-test api-health

api-install:
	$(PYTHON) -m pip install -r apps/api/requirements.txt

api-dev:
	$(PYTHON) -m uvicorn app.main:app --reload --app-dir apps/api

api-test:
	$(PYTHON) -m unittest discover -s apps/api/tests -t apps/api

api-health:
	curl http://localhost:8000/health
