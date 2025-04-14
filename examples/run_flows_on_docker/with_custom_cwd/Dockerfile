# run `docker build` from the directory containing this Dockerfile
FROM prefecthq/prefect:3.3.4-python3.13

ENV VIRTUAL_ENV=/app/.venv

WORKDIR /app

RUN uv venv --python 3.13 && . $VIRTUAL_ENV/bin/activate
COPY requirements.txt requirements.txt

RUN uv pip install -r requirements.txt

COPY workflow.py workflow.py
