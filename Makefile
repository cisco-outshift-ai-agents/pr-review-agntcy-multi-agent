# Variables
VENV_DIR = venv

ifeq ($(shell test -d .venv && echo 1 || echo 0), 1)
     VENV_DIR = .venv
endif

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

	$(POETRY) install

	$(PIP) install ruff

# Run unit tests
.PHONY: test
test:
	$(PYTEST)

# Run ruff linters 
.PHONY: lint
lint:
	$(VENV_DIR)/bin/ruff check

# Format code using ruff
.PHONY: format
format:
	$(VENV_DIR)/bin/ruff format

.PHONY: setup
setup:
	brew update && brew install pyenv && \
	pyenv install 3.12.9

	~/.pyenv/versions/3.12.9/bin/python3 -m venv .venv && \
	source .venv/bin/activate

	pip install -U pip setuptools; \
	pip install poetry && \
	poetry install

	npm install --global smee-client

	brew tap hashicorp/tap
	brew install hashicorp/tap/terraform

	brew install tflint
