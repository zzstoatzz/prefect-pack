FROM prefecthq/prefect:3-python3.13

ENV UV_SYSTEM_PYTHON=1

RUN uv pip install 'logfire[fastapi,sqlalchemy]>=3.14.0' prefect-redis
