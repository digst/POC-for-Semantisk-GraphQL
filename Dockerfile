FROM python:3.11

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION="1.8" \
    POETRY_HOME=/opt/poetry \
    VIRTUAL_ENV="/venv"
ENV PATH="$VIRTUAL_ENV/bin:$POETRY_HOME/bin:$PATH"

# Install poetry in an isolated environment
RUN python -m venv $POETRY_HOME \
    && pip install --no-cache-dir poetry==${POETRY_VERSION}

# Install project in another isolated environment
RUN python -m venv $VIRTUAL_ENV
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root

COPY digstsgql ./digstsgql

# Properly create HTTPS URLs in url_for() when behind reverse proxy
ENV FORWARDED_ALLOW_IPS=*

CMD ["uvicorn", "--factory", "digstsgql.app:create_app", "--host", "0.0.0.0"]

# Add build version to the environment last to avoid build cache misses
ARG COMMIT_TAG
ARG COMMIT_SHA
ENV COMMIT_TAG=${COMMIT_TAG:-HEAD} \
    COMMIT_SHA=${COMMIT_SHA}
