from prefect import flow, serve
from prefect.events import DeploymentEventTrigger, ResourceSpecification


@flow
def some_flow():
    print("Hello, world!")


@flow
def triggered_on_foo_tag_flow():
    print("i happen when a flow run with tag foo completes")


triggered_on_foo_tag = DeploymentEventTrigger(
    expect={"prefect.flow-run.Completed"},
    match_related=ResourceSpecification.model_validate(
        {"prefect.resource.id": "prefect.tag.foo"}
    ),
)

if __name__ == "__main__":
    serve(
        some_flow.to_deployment(name="some_flow", tags=["foo"]),
        triggered_on_foo_tag_flow.to_deployment(
            name="triggered_on_foo_tag_flow",
            triggers=[triggered_on_foo_tag],
        ),
    )
