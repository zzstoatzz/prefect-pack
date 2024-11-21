FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*


RUN uv pip install prefect

ENTRYPOINT ["uv", "run", "prefect", "worker", "start", "--pool", "local"]

# docker build -t zzstoatzz/prefect-worker:latest -f examples/run_a_prefect_worker/on_docker/Dockerfile .
# docker run -d --rm --name prefect-worker --env-file .env zzstoatzz/prefect-worker:latest