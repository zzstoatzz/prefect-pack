# Check for uv installation
check-uv:
    #!/usr/bin/env sh
    if ! command -v uv >/dev/null 2>&1; then
        echo "uv is not installed or not found in expected locations."
        case "$(uname)" in
            "Darwin")
                echo "To install uv on macOS, run one of:"
                echo "• brew install uv"
                echo "• curl -LsSf https://astral.sh/uv/install.sh | sh"
                ;;
            "Linux")
                echo "To install uv, run:"
                echo "• curl -LsSf https://astral.sh/uv/install.sh | sh"
                ;;
            *)
                echo "To install uv, visit: https://github.com/astral-sh/uv"
                ;;
        esac
        exit 1
    fi

# Install development dependencies with all extras
install: check-uv
    echo "Installing dependencies with all extras..."
    uv sync --dev --all-extras

# Run linting checks
lint: check-uv
    uv run --with-editable '.[dev]' pre-commit run --all-files --show-diff-on-failure

# Clean up Python cache files
clean:
    echo "Cleaning up"
    bash -c 'deactivate || true'
    rm -rf .venv
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Deploy all Prefect deployments
deploy-all: check-uv
    uv run prefect --no-prompt deploy --all

# Run tests
test: check-uv
    uv run --with-editable '.[dev]' pytest

# Set Prefect cloud workspace
psw: check-uv
    uv run prefect cloud workspace set

# Build and serve documentation
docs: check-uv
    echo "congratulations, you have found a TODO! 🙂"