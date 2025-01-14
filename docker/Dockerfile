# Use the official Python image from the Docker Hub
FROM public.ecr.aws/lambda/python:3.12 as base

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create true
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-root

FROM public.ecr.aws/lambda/python:3.12 as build

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=base /app/.venv/lib/python3.12/site-packages/ ${LAMBDA_TASK_ROOT}/
COPY src/ ${LAMBDA_TASK_ROOT}/

CMD ["main.handle_event"]