# prefect pack

This project serves as a GitHub repository template for bootstrapping a new Prefect project.

Included in this template is a basic project structure for writing, testing, and deploying Prefect flows:
  - `pyproject.toml` file for managing project dependencies and configuration (testing, linting etc)
  - `flows/` directory for storing Prefect flow files
  - `prefect.yaml` configuration file for storing deployment definitions
  - `src/prefect_pack` package for storing flow steps and utility functions
  - a skeleton test suite using `pytest` and fixtures for setting up a temporary Prefect environment

> [!NOTE]
> You don't need to publish `prefect-pack` to PyPI, or install any distribution. You can install it locally and in your images using `pip install .` or `pip install -e .`.

## Using the Template

To use this template for your own project:

1. Click the "Use this template" button on the GitHub repository page.
2. Provide a name for your new repository and select the desired visibility (public or private).
3. Clone the newly created repository to your local machine and modify the project as needed.


## Setup Guide

### Prerequisites

- Python 3.10+
- `prefect` >= 2.18.3
- Docker

### Installation

1. Change to the project directory:
   ```
   cd your-prefect-project
   ```

2. Install the package:
   ```install
   uv venv 
   uv pip install --system .
   ```

> [!TIP]
> What is `uv`? It's a really fast `pip` made by the same folks who made `ruff`. Check it out [here](https://github.com/astral-sh/uv?tab=readme-ov-file#getting-started). Install with `curl -LsSf https://astral.sh/uv/install.sh | sh`. You can instead use `pip` if you like waiting for dependencies to resolve.

### Configuration

Update the `prefect.yaml` file with your project-specific configuration, such as Docker image build settings, remote push locations, and deployment configurations.

### Adding Flows and Tests

- Place your Prefect flow files in the `flows/` directory.
- Write corresponding tests for your flows in the `tests/flows/` directory.

### Running Tests

To run the test suite, use the following command:

```
pytest -n auto -vvv
```

This command will run the tests in parallel (`-n auto`) with verbose output (`-vvv`).

### Deploying Flows

The template includes a GitHub Actions workflow (`deploy.yaml`) to automatically deploy flows to a Prefect Cloud workspace when changes are pushed to the `main` branch.

To set up the deployment workflow:

1. Set the necessary secrets in your GitHub repository.
2. Ensure that the `deploy.yaml` workflow file is present in the `.github/workflows` directory.
3. Push your changes to the `main` branch to trigger the deployment workflow.


> [!TIP]
> Use `gh secret set -f .env` to set all environment variables in your `.env` file as GitHub Actions secrets in the remote repository.

## Project Structure Overview

```
.
├── .github
│   └── workflows
│       └── deploy.yaml
│       └── tests.yaml
├── flows
│   └── hello.py
├── prefect.yaml
├── src
│   └── prefect_pack
│       ├── __init__.py
│       ├── steps
│       └── utils.py
└── tests
    ├── conftest.py
    └── flows
        └── test_hello.py
```

- `flows/`: Directory to store your Prefect flow files.
- `prefect.yaml`: Configuration file for deploying flows.
- `src/prefect_pack/`: Package source code - contains flow steps and utility functions.
  - `steps/`: Directory for custom deployment step definitions.
  - `utils.py`: Your custom utility functions you reuse often in your flows.
- `tests/`: Directory for test files.
  - `flows/`: Directory for flow-specific tests.
- `.github/workflows/`: Directory for GitHub Actions workflows.

## Contributing

Contributions to this template are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

