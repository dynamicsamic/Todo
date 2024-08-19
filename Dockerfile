FROM python:3.12.3-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY main.py /app
COPY hypercorn.toml /app
COPY requirements.txt /app

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache

COPY src/ /app

EXPOSE 8080
