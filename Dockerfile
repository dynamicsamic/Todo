FROM python:3.12.3-slim-bookworm

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install -U pdm
ENV PDM_CHECK_UPDATE=false

COPY main.py hypercorn.toml pdm.lock pyproject.toml /app/

RUN pdm install --check --prod --no-editable

COPY src/ /app/src

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080
