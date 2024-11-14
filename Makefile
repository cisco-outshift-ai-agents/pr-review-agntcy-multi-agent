# Variables
VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip
POETRY = $(VENV_DIR)/bin/poetry
PYTEST = $(VENV_DIR)/bin/pytest

# Default target
.PHONY: all
all: test

# Create and activate virtual environment
.PHONY: venv
venv:
	python3 -m venv $(VENV_DIR)

# Install dependencies
.PHONY: install
install:
	$(PIP) install poetry
# no root because we don't want to install alfred as a project
	$(POETRY) install --no-root

	$(PIP) install ruff

# Run unit tests
.PHONY: test
test:
	$(PYTEST)

.PHONY: lint
lint:
	$(VENV_DIR)/bin/ruff check

.PHONY: format
format:
	$(VENV_DIR)/bin/ruff format