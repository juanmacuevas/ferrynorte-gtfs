# ferrynorte-gtfs — build ferry GTFS feeds from operator sources.
# Requires uv (https://docs.astral.sh/uv/). Run `make setup` once.

OPERATOR ?= los-reginas
OPDIR := operators/$(OPERATOR)
SRC    := $(OPDIR)/src
GTFS   := $(OPDIR)/gtfs
BUILD  := builds/$(OPERATOR)

.DEFAULT_GOAL := help
.PHONY: help setup build check validate zip clean

help: ## List available targets
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
	@echo "  (override the operator with: make build OPERATOR=<name>)"

setup: ## Install dependencies into a uv-managed venv
	uv sync

build: ## Rebuild the operator's GTFS .txt files from its source PDFs
	uv run python $(SRC)/extract.py
	uv run python $(SRC)/build.py

check: ## Rebuild in memory and diff vs committed .txt (regression test, writes nothing)
	uv run python $(SRC)/extract.py
	uv run python $(SRC)/build.py --check

validate: ## Validate an operator's GTFS feed (structural + referential checks)
	python3 scripts/validate.py $(GTFS)

zip: validate ## Package the operator's feed into builds/<op>/ (validates first)
	python3 scripts/zip_feed.py $(GTFS) $(BUILD)/$(OPERATOR)_gtfs.zip

clean: ## Remove the uv venv, local builds and Python caches
	rm -rf .venv builds
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
