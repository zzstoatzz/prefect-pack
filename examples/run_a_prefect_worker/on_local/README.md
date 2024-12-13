run a prefect server in the background
```
docker run -p 4200:4200 --rm ghcr.io/astral-sh/uv:python3.12-bookworm-slim uvx prefect server start --host 0.0.0.0
```

now from repo root allow the smoke test to be run
```
chmod +x examples/run_a_prefect_worker/on_local/smoke_test
```

run the smoke test
```
./examples/run_a_prefect_worker/on_local/smoke_test
```
