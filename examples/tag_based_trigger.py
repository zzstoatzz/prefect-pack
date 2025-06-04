from prefect import flow, serve
from prefect.events import DeploymentEventTrigger, ResourceSpecification


@flow
def some_flow():
    print("Hello, world!")


@flow
def triggered_on_foo_tag_flow():
    print("i happen when a flow run with tag foo completes")


trigger_on_foo_tag = DeploymentEventTrigger(
    expect={"prefect.flow-run.Completed"},
    match_related=ResourceSpecification.model_validate(
        {"prefect.resource.id": "prefect.tag.foo"}
    ),
)

if __name__ == "__main__":
    serve(
        some_flow.to_deployment(name="some flow", tags=["foo"]),
        triggered_on_foo_tag_flow.to_deployment(
            name="triggered on foo tag",
            triggers=[trigger_on_foo_tag],
        ),
    )
