.PHONY: deploy test all

all: deploy test

deploy:
	cd ../.. && prefect --no-prompt deploy --all --prefect-file flows/be_modal/prefect.yaml

test:
	prefect deployment run 'hello-world/nested-project-flow' --watch
