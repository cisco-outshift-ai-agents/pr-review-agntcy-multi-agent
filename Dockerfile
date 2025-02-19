# Base image for building Python dependencies
FROM python:3.12.6-slim AS base

# Set working directory
WORKDIR /app

# Install Poetry globally
RUN pip install --no-cache-dir poetry

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to use a local virtual environment and install dependencies
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-root

# Build image for running the application with additional tools
FROM python:3.12.6-slim AS build

# Set working directory for the application
WORKDIR /app

# Install required system tools and clean up to reduce image size
RUN apt-get update && \
    apt-get install -y \
    unzip \
    jq \
    ca-certificates \
    curl \
    wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN curl -Lo /tmp/terraform.zip https://releases.hashicorp.com/terraform/1.6.1/terraform_1.6.1_linux_amd64.zip && \
    unzip /tmp/terraform.zip -d /usr/local/bin/ && \
    rm -f /tmp/terraform.zip

# Install TFLint
RUN curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash

# Copy Python dependencies from the base image
COPY --from=base /app/.venv/ /app/.venv/

# Copy source code into the working directory
COPY src/ /app/src/

# Set environment variables to use the virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Default command to run the Python script with the handler name as the first argument
CMD ["python3", "src/main_local.py"]
