.PHONY: install clean deployments test lint

install:
	uv sync --dev --all-extras

lint:
	uv run --with-editable '.[dev]' pre-commit run --all-files --show-diff-on-failure


clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

deployments:
	uv run prefect --no-prompt deploy --all

test:
	uv run --with-editable '.[dev]' pytest

psw:
	uv run prefect cloud workspace set