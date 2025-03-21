# Use the official Python image from the Docker Hub
FROM ghcr.io/cisco-outshift-alfred/lambda/python:3.12.9 as base

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create true
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-root

FROM public.ecr.aws/lambda/python:3.12 as build

WORKDIR ${LAMBDA_TASK_ROOT}

RUN dnf update -y && \
    dnf install -y \
    unzip \
    jq \
    ca-certificates && \
    dnf clean all

# Install Terraform, Alfred will run static analyzers on the repo
RUN curl -Lo /tmp/terraform.zip https://releases.hashicorp.com/terraform/1.6.1/terraform_1.6.1_linux_amd64.zip && \
    unzip /tmp/terraform.zip -d /usr/local/bin/ && \
    rm -f /tmp/terraform.zip

# Install tflint for the same reasons as above
RUN curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash

COPY --from=base /app/.venv/lib/python3.12/site-packages/ ${LAMBDA_TASK_ROOT}/
COPY src/ ${LAMBDA_TASK_ROOT}/

CMD ["main.handle_event"]
