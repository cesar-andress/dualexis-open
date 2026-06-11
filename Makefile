.PHONY: install reproduce test check lint docker

install:
	pip install -e ".[dev]"

reproduce:
	bash artifact/commands.sh

test:
	python3.12 -m pytest tests/unit -q

check:
	ruff format --check .
	ruff check .
	mypy dualexis tests
	$(MAKE) test

lint:
	ruff check .
	ruff format .

docker:
	docker build -t tsgg-reference:v1.0.4 .
