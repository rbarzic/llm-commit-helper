# llm-commit-helper Makefile
#
# Works from any directory — HELPER_DIR is always the Makefile's own location.
HELPER_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

VENV     := $(HELPER_DIR).venv
PYTHON   := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip

PROMPT_FILE ?= $(HELPER_DIR)prompt_example.txt

# LLM settings — defaults match the vllm-lan provider in opencode.json
LLM_PROVIDER ?= vllm-lan
LLM_MODEL    ?= nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4

# Full model identifier passed to opencode run -m
_OPENCODE_MODEL := $(LLM_PROVIDER)/$(LLM_MODEL)

# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------

.PHONY: commit
## Generate a commit message from staged changes using opencode
commit:
	@prompt=$$(cat $(PROMPT_FILE) && llm-commit-helper) && \
	 opencode run -m $(_OPENCODE_MODEL) --title "commit-message" "$$prompt"

.PHONY: diff
## Show llm-commit-helper output without calling the LLM (useful for debugging)
diff:
	@llm-commit-helper

.PHONY: diff-verbose
## Same as diff but with diagnostic output on stderr
diff-verbose:
	@llm-commit-helper --verbose

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install build twine

.PHONY: install
## Install the package in editable mode (pip install -e .)
install: $(VENV)
	$(PIP) install -e $(HELPER_DIR)

.PHONY: test
## Run the unit test suite
test: $(VENV)
	cd $(HELPER_DIR) && $(PYTHON) -m pytest tests/ -v

.PHONY: build
## Build source distribution and wheel (output in dist/)
build: $(VENV)
	cd $(HELPER_DIR) && $(PYTHON) -m build

.PHONY: publish
## Upload to PyPI (requires twine and a valid ~/.pypirc or TWINE_* env vars)
publish: build
	cd $(HELPER_DIR) && $(PYTHON) -m twine upload dist/*

.PHONY: publish-test
## Upload to TestPyPI first (safe dry-run before a real release)
publish-test: build
	cd $(HELPER_DIR) && $(PYTHON) -m twine upload --repository testpypi dist/*

.PHONY: help
help:
	@echo "llm-commit-helper"
	@echo ""
	@echo "Variables (override on the command line):"
	@echo "  LLM_PROVIDER  Provider key in opencode.json  (default: $(LLM_PROVIDER))"
	@echo "  LLM_MODEL     Model name within the provider (default: $(LLM_MODEL))"
	@echo "  PROMPT_FILE   Path to the prompt prefix file (default: $(PROMPT_FILE))"
	@echo ""
	@echo "Targets:"
	@echo "  install       pip install -e . (editable install)"
	@echo "  build         Build sdist + wheel into dist/"
	@echo "  publish       Build and upload to PyPI"
	@echo "  publish-test  Build and upload to TestPyPI"
	@echo "  commit        Generate a commit message via opencode"
	@echo "  diff          Show the processed diff without calling the LLM"
	@echo "  diff-verbose  Same as diff with diagnostic output"
	@echo "  test          Run the unit tests"
	@echo "  help          Show this message"

.DEFAULT_GOAL := help
