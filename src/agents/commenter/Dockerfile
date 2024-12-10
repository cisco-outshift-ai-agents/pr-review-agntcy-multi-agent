FROM python:3.12.7-bookworm AS builder
ARG POETRY_VERSION=1.8.3
ARG AGENT_NAME=commenter

WORKDIR /opt/alfred
RUN python -m pip install poetry=="${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./

RUN bash -c "POETRY_VIRTUALENVS_IN_PROJECT=true poetry install --no-cache --no-interaction --no-ansi --no-root --compile --only main"

FROM python:3.12.7-bookworm 
COPY --from=builder /opt/alfred /opt/alfred

WORKDIR /opt/alfred
COPY src/agents/${AGENT_NAME} ./agents/${AGENT_NAME}  
COPY src/agents/models.py ./agents/models.py
COPY src/utils utils
COPY src/config config
COPY src/auth.py auth.py
COPY src/pr_graph pr_graph

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV VENV_PATH="/opt/alfred/.venv"
ENV PATH="$VENV_PATH/bin:$PATH"

ENV GITHUB_APP_PRIVATE_KEY_FILE GITHUB_APP_PRIVATE_KEY_FILE
ENV GITHUB_APP_PRIVATE_KEY GITHUB_APP_PRIVATE_KEY
ENV GITHUB_APP_ID GITHUB_APP_ID

ENTRYPOINT [ "python", "-m", "agents.commenter.commenter" ]
