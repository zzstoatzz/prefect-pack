.PHONY: deploy test all

all: deploy test

deploy:
	cd ../.. && uv run prefect --no-prompt deploy --all --prefect-file flows/be_modal/prefect.yaml

test:
	uv run prefect deployment run 'hello-world/nested-project-flow' --watch
