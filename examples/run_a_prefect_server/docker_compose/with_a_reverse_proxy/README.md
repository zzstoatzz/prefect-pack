# Example: Running Prefect Server with Nginx Reverse Proxy via Docker Compose

This example demonstrates how to set up a Prefect server behind an Nginx reverse proxy using Docker Compose. This is a common pattern for exposing the Prefect UI and API externally, potentially adding SSL termination or custom domain names later.

## Files

*   `compose.yaml`: Defines the Docker services for the Prefect server and Nginx.
*   `nginx.conf`: Basic Nginx configuration to proxy requests to the Prefect server.

## Prerequisites

*   Docker and Docker Compose installed.

## Running the Example

1.  **Start the Services:**
    Navigate to this directory in your terminal and run:
    ```bash
    docker compose up -d
    ```
    This will build (if necessary) and start the `prefect-server` and `nginx` containers in the background.

2.  **Access Prefect UI:**
    Open your web browser and navigate to `http://localhost`. Nginx will proxy the request to the Prefect server container, and you should see the Prefect UI.

3.  **Configure Prefect Client (Optional):**
    If you want to interact with this server using the Prefect CLI or client library from your host machine or another container, configure the API URL:
    ```bash
    prefect config set PREFECT_API_URL=http://localhost/api/
    ```
    You should then be able to interact with the server, e.g., `prefect worker start --pool default-agent-pool` (or your specific pool name).

## Configuration Notes

*   **Nginx:** The `nginx.conf` proxies both `/` (for the UI) and `/api` to the `prefect-server` service on port 4200 (the default Prefect server port). It includes headers necessary for WebSocket connections (`Upgrade`, `Connection`) which are used by Prefect.
*   **Prefect Server:** The `compose.yaml` uses the standard `prefecthq/prefect` image. Environment variables like `PREFECT_UI_URL` and `PREFECT_API_URL` are commented out; Prefect typically relies on the `X-Forwarded-*` headers set by the proxy to determine the correct external URLs.
*   **Authentication:** The example does not enable Prefect server authentication by default. If you enable it (e.g., by setting `PREFECT_SERVER_API_AUTH_STRING`), you'll need to uncomment the `Authorization` header lines in `nginx.conf` to ensure credentials are passed through.
*   **HTTPS/SSL:** This example uses HTTP. For production, you would typically configure Nginx to handle HTTPS, often using Let's Encrypt for certificates.
*   **Domain Name:** Replace `localhost` in `nginx.conf` and potentially the Prefect environment variables if you are deploying this behind a specific domain name.

## Stopping the Services

To stop and remove the containers, run:
```bash
docker compose down
```
To remove the persistent volume as well:
```bash
docker compose down -v
``` 