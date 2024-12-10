FROM python:3.12.7-bookworm AS builder
ARG POETRY_VERSION=1.8.3
ARG AGENT_NAME=title_reviewer

WORKDIR /opt/alfred
RUN python -m pip install poetry=="${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./

RUN bash -c "POETRY_VIRTUALENVS_IN_PROJECT=true poetry install --no-cache --no-interaction --no-ansi --no-root --compile --only main"

FROM python:3.12.7-bookworm 
COPY --from=builder /opt/alfred /opt/alfred

COPY src/agents/${AGENT_NAME} ./agents/${AGENT_NAME}  
COPY src/agents/models.py ./agents/models.py
COPY src/utils utils
COPY src/config config
COPY src/auth.py auth.py
COPY src/pr_graph pr_graph

ENV GITHUB_APP_PRIVATE_KEY_FILE GITHUB_APP_PRIVATE_KEY_FILE
ENV GITHUB_APP_PRIVATE_KEY GITHUB_APP_PRIVATE_KEY
ENV GITHUB_APP_ID GITHUB_APP_ID
ENV agency_provider agency_provider

ENV AZURE_OPENAI_ENDPOINT='https://prcoach-project-agents.openai.azure.com'
ENV AZURE_OPENAI_DEPLOYMENT='gpt-4o'
ENV AZURE_OPENAI_API_KEY=''
ENV AZURE_OPENAI_API_VERSION='2024-08-01-preview'

# Config for VertexAI based model
ENV VERTEXAI_MODEL='claude-3-5-sonnet@20240620'
ENV VERTEXAI_GCP_REGION='europe-west1'

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV VENV_PATH="/opt/alfred/.venv"
ENV PATH="$VENV_PATH/bin:$PATH"



ENTRYPOINT [ "python","-m", "agents.title_reviewer.title_reviewer" ]
