# Use the official Python image from the Docker Hub
FROM public.ecr.aws/lambda/python:3.12 as builder

WORKDIR /app

RUN pip install poetry

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN poetry install --no-root && \
    rm -rf $POETRY_CACHE_DIR

FROM public.ecr.aws/lambda/python:3.12 as runtime

ENV VIRTUAL_ENV=.venv \
    PATH=".venv/bin:$PATH"

COPY --from=builder app/${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY src .

CMD ["main.handle_event"]