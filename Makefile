# omnifocus-mcp — common tasks. All targets are phony; run with `make <target>`.

UV ?= uv
PYTHON ?= $(UV) run python
PYTEST ?= $(UV) run pytest
COVERAGE ?= $(UV) run coverage

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\nTargets:\n"} \
	     /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install:  ## Sync venv + dev deps
	$(UV) sync --extra dev

.PHONY: test
test:  ## Run unit tests (no OmniFocus needed)
	$(PYTEST)

.PHONY: test-integration
test-integration:  ## Run live integration tests — MUTATES real OmniFocus DB (scratch prefix __mcp_test__)
	$(PYTEST) -m integration

.PHONY: test-all
test-all:  ## Run unit + integration
	$(PYTEST) -m 'integration or not integration'

.PHONY: smoke
smoke:  ## Read-only smoke against live OmniFocus — safe, no mutations
	$(PYTHON) tests/_smoke.py

.PHONY: coverage
coverage:  ## Unit tests with coverage report
	$(COVERAGE) run -m pytest
	$(COVERAGE) report -m

.PHONY: coverage-html
coverage-html:  ## Coverage HTML report in htmlcov/
	$(COVERAGE) run -m pytest
	$(COVERAGE) html
	@echo "Open htmlcov/index.html"

.PHONY: server
server:  ## Run the MCP server on stdio (useful for manual probing)
	$(UV) run omnifocus-mcp

.PHONY: install-tool
install-tool:  ## Install `omnifocus-mcp` onto PATH via uv tool install (for client configs)
	$(UV) tool install --from . omnifocus-mcp --force

.PHONY: uninstall-tool
uninstall-tool:  ## Uninstall the `omnifocus-mcp` tool
	$(UV) tool uninstall omnifocus-mcp

.PHONY: scratch-clean
scratch-clean:  ## Remove any __mcp_test__* residue left in OmniFocus from a failed integration run
	@osascript -l JavaScript -e 'function run() { return Application("OmniFocus").evaluateJavascript("var d=[];flattenedProjects.filter(function(p){return p.name.indexOf(\"__mcp\")===0;}).forEach(function(p){d.push(p.name); deleteObject(p);});flattenedTags.filter(function(t){return t.name.indexOf(\"__mcp\")===0;}).forEach(function(t){d.push(\"tag:\"+t.name); deleteObject(t);});JSON.stringify({deleted:d});"); }'

.PHONY: clean
clean:  ## Remove caches, build artifacts, coverage data
	rm -rf .coverage htmlcov .pytest_cache
	rm -rf build dist *.egg-info src/*.egg-info
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +

.PHONY: distclean
distclean: clean  ## clean + remove the virtualenv
	rm -rf .venv
