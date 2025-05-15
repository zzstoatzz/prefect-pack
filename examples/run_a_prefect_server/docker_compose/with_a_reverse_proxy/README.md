# Prefect Server with Nginx Reverse Proxy

A minimal example of running Prefect server behind Nginx using Docker Compose.

## Quick Start

```bash
docker compose up -d
```

Access the UI at `http://localhost`

## Key Configuration

* `PREFECT_UI_API_URL`: Required for reverse proxy setups. Tells the UI where to make API calls.
* `PREFECT_UI_URL`: Used by server and CLI for constructing UI URLs.

Both must point to the external URL via Nginx (e.g., `http://localhost/api/` and `http://localhost/`).

## Files

* `compose.yaml`: Docker services for Prefect server and Nginx
* `nginx.conf`: Nginx configuration for proxying UI and API requests

## Client Setup

To use this server from your host machine:

```bash
prefect config set PREFECT_API_URL=http://localhost/api/
```

## Cleanup

```bash
docker compose down        # Stop containers
docker compose down -v    # Stop and remove volumes
``` 