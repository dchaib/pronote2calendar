# Build stage
FROM python:3.13.9-slim AS builder

RUN python -m pip install --upgrade pip
RUN pip install poetry==2.2.1

ENV POETRY_VIRTUALENVS_IN_PROJECT=true
COPY pyproject.toml poetry.lock README.md .
COPY src/ ./src

RUN poetry install --only=main --no-root

# Final stage
FROM python:3.13.9-alpine
WORKDIR /app

COPY --from=builder /src /app
COPY --from=builder /.venv /app/.venv
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "pronote2calendar.main"]