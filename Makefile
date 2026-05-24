.PHONY: install build build-release build-debug build-ccache clean test lint run docs

install:
	pip install -r requirements.txt
	pip install -e .

build:
	ndk-build

build-release:
	python3 scripts/build_ndk.py

build-debug:
	python3 scripts/build_ndk.py libmod_debug.so src/main.cpp -g -O0

build-ccache:
	CCACHE=$$(command -v ccache) python3 scripts/build_ndk.py libmod_cc.so src/main.cpp -flto=thin

clean:
	rm -rf libs/*.so libs/*.o obj/ build/ __pycache__/ .pytest_cache/

test:
	python3 -m pytest tests/ -v

lint:
	ruff check src/ tests/ || echo "install ruff: pip install ruff"

typecheck:
	mypy src/ --ignore-missing-imports || true

run:
	python3 -m src.server

docs:
	python3 scripts/generate_docs.py
	@echo "Docs regenerated: docs/api.md"
	@echo "  README.md      - Architecture overview"
	@echo "  AGENTS.md       - Agent instructions"
	@echo "  SKILL.md        - opencode skill definition"
	@echo "  examples/       - Runnable usage examples"
	@echo "  CHANGELOG.md    - Release history"