# Example: Deploying a Flow to Docker with Custom CWD and Dependencies

This example demonstrates how to deploy a Prefect flow to a Docker container, ensuring it runs within a specific working directory (`/app` in this case) and includes necessary Python dependencies (`pandas`).

The deployment is handled entirely via a Python script (`workflow.py`) using `flow.deploy`, which leverages the provided `Dockerfile` to build and push the image. This avoids the need for a `prefect.yaml` file solely for managing the working directory or build process.

## Prerequisites

1.  **Docker:** Ensure Docker Desktop or Docker Engine is running.
2.  **Prefect Server/Cloud:** Have a Prefect server running locally (`prefect server start`) or be logged into Prefect Cloud (`prefect cloud login`).
3.  **Docker Work Pool:** Create a Docker work pool if you don't have one:
    ```bash
    prefect work-pool create --type docker docker-work
    ```
4.  **(Optional) Python Environment:** While the flow runs in Docker, you may want to install dependencies locally to run the deployment script. Use [uv](https://docs.astral.sh/uv/) to create a virtual environment and install the dependencies:
    ```bash
    uv venv --python 3.13 && source .venv/bin/activate
    uv pip install -r requirements.txt  # Install packages needed to *deploy*
    ```

## Running the Example

1.  **Deploy the Flow:**
    Navigate to this directory in your terminal and run the deployment script:
    ```bash
    python workflow.py
    ```
    This command will:
    *   Build a Docker image using the `Dockerfile` in this directory. The `Dockerfile` sets the `WORKDIR` to `/app`, copies `requirements.txt` and `workflow.py`, and installs the dependencies (`prefect`, `pandas`) listed in `requirements.txt`.
    *   Push the image to a registry (if configured in your Docker setup or Prefect Docker integration) or use the local Docker daemon's image cache. By default, the image is named `zzstoatzz/prefect-pack:the-work-is-mysterious-and-important`.
    *   Create or update a Prefect deployment named `the-work-is-mysterious-and-important` targeting the `docker-work` pool.

2.  **Start a Worker:**
    In a separate terminal, start a Prefect worker to poll the `docker-work` pool:
    ```bash
    prefect worker start --pool 'docker-work'
    ```
    The worker will automatically pick up scheduled runs for the deployment and execute them in new Docker containers based on the image built in step 1.

3.  **(Optional) Trigger a Run:**
    You can manually trigger a run:
    ```bash
    prefect deployment run 'the-work-is-mysterious-and-important/the-work-is-mysterious-and-important'
    ```
    The worker will detect this run and execute it. Check the worker logs or the Prefect UI to see the output, including the pandas DataFrame printout.

## Managing Dependencies

Python dependencies required by your flow *inside the Docker container* should be added to `requirements.txt`. The `Dockerfile` ensures these are installed when the image is built during the `python workflow.py` step.
