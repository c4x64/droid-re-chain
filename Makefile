.PHONY: install build build-release build-debug build-ccache clean test lint run docs

install:
	pip install -r requirements.txt
	pip install -e .

build:
	ndk-build

build-release:
	python3 -c "from src.server import mcp; mcp._tool_manager.get_tool('ndk_build_module').fn()" || \
	python3 scripts/build_ndk.py

build-debug:
	python3 -c "from src.server import mcp; mcp._tool_manager.get_tool('ndk_build_debug').fn()"

build-ccache:
	python3 -c "from src.server import mcp; mcp._tool_manager.get_tool('ndk_build_ccache').fn()"

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
	@echo "Documentation:"
	@echo "  README.md      - Architecture overview"
	@echo "  AGENTS.md       - Agent instructions"
	@echo "  SKILL.md        - opencode skill definition"
	@echo "  examples/       - Runnable usage examples"
	@echo "  docs/api.md     - API reference (generated)"
	python3 -c "
import json
from src.server import mcp
tools = mcp._tool_manager._tools
cats = {}
for name in sorted(tools):
    prefix = name.split('_')[0] if '_' in name else name
    cats.setdefault(prefix, []).append(name)
for cat, names in sorted(cats.items()):
    print(f'  {cat}: {len(names)} tools')
print(f'  TOTAL: {len(tools)} tools')
"
