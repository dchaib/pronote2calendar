# Build stage
FROM python:3.14.0-slim AS builder

RUN python -m pip install --upgrade pip
RUN pip install poetry==2.2.1

ENV POETRY_VIRTUALENVS_IN_PROJECT=true
COPY pyproject.toml poetry.lock README.md .
COPY src/ ./src

RUN poetry install --only=main --no-root

# Final stage
FROM python:3.14.0-alpine
WORKDIR /app

COPY --from=builder /src /app
COPY --from=builder /.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "pronote2calendar.main"]