FROM python:3.11-slim

RUN apt-get update && apt-get install -y git

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1

RUN pip install uv

COPY flows/with_special_deps/requirements.txt requirements.txt

RUN uv pip install -r requirements.txt
