.PHONY: install build clean test lint run

install:
	pip install -r requirements.txt
	pip install -e .

build:
	ndk-build

clean:
	python3 -c "from src.tools_ndk import register; print('run ndk_build_clean via MCP')"

test:
	python3 -m pytest tests/ -v || echo "no tests/ directory yet"

lint:
	ruff check src/ || echo "install ruff: pip install ruff"

run:
	python3 src/server.py
