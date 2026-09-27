FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv==0.4.10

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY src/ src/
RUN uv sync --no-dev


FROM python:3.12-slim AS runtime

RUN groupadd -r nonroot && useradd -r -g nonroot nonroot

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN chown -R nonroot:nonroot /app

USER nonroot

CMD ["python", "-m", "agent_runtime.main"]
