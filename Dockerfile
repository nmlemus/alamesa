FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir . psycopg2-binary


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH"

RUN useradd --uid 1001 --system --no-create-home appuser

COPY --from=builder /venv /venv

WORKDIR /app
COPY alembic.ini .
COPY alembic/ alembic/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["mesadigital-api"]
