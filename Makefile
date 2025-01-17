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
	pyenv install 3.12.6

	~/.pyenv/versions/3.12.6/bin/python3 -m venv .venv && \
	source .venv/bin/activate

	pip install -U pip setuptools; \
	pip install poetry && \
	poetry install

	npm install --global smee-client

# Start a smee client which routes HTTP requests to the local lambda runtime
start-smee-for-lambda:
	npx smee -u https://smee.io/$(smee_id) -t http://localhost:3000

# Build and start the lambda image locally using sam
start-lambda: build-lambda-image
# sam doesn't support volumes currently so we pass in the contents of the key file as env var
	cd deployment/local_invocation && sam build --hook-name terraform
	cd deployment/local_invocation && sam local start-api --hook-name terraforms --host 127.0.0.1 --port 3000

# Build the lambda image
.PHONY: build-lambda-image
build-lambda-image:
	docker build -f docker/Dockerfile --platform=linux/amd64 -t alfred:local .
