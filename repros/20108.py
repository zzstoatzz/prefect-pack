"""
Repro for https://github.com/PrefectHQ/prefect/issues/20108
Queue-scoped workers miss rescheduled flow runs from automation actions.

This script:
1. Deploys a flow to a process work pool
2. Triggers a run that fails
3. Uses force=True to reschedule it to SCHEDULED
4. Checks if the run appears in the work queue (Redis polling)

Run with: uv run python repros/20108.py
Make sure you're on the stg profile: uv run prefect profile use stg
"""

import asyncio
import sys

from prefect import flow
from prefect.client.orchestration import get_client
from prefect.states import Scheduled

WORK_POOL = "process"
WORK_QUEUE = "default"


@flow(log_prints=True)
def failing_flow(should_fail: bool = True):
    if should_fail:
        raise ValueError("Intentional failure for testing issue #20108")
    print("Flow completed successfully!")


async def force_reschedule(flow_run_id):
    """Force reschedule a flow run and check if it appears in the work queue."""
    async with get_client() as client:
        # Read the flow run
        flow_run = await client.read_flow_run(flow_run_id)
        print(f"\nFlow run: {flow_run.id}")
        print(f"  state: {flow_run.state.type}")
        print(f"  work_queue_id: {flow_run.work_queue_id}")

        if not flow_run.work_queue_id:
            print("ERROR: Flow run has no work_queue_id!")
            return

        # Force reschedule to SCHEDULED
        print("\nForce-rescheduling to SCHEDULED...")
        result = await client.set_flow_run_state(
            flow_run_id=flow_run.id,
            state=Scheduled(),
            force=True,
        )
        print(f"Result: {result}")

        # Re-read the flow run to check state
        updated_run = await client.read_flow_run(flow_run.id)
        print(f"Updated state: {updated_run.state.type}")

        # Check if run is in the work queue
        print("\nChecking work queue for the run...")
        runs = await client.get_scheduled_flow_runs_for_work_pool(
            work_pool_name=WORK_POOL,
            work_queue_names=[WORK_QUEUE],
        )
        run_ids = [r.flow_run.id for r in runs]
        if flow_run.id in run_ids:
            print(f"SUCCESS: Flow run {flow_run.id} is in the work queue!")
        else:
            print(f"FAILURE: Flow run {flow_run.id} NOT found in work queue")
            print(f"  Runs in queue: {[str(r) for r in run_ids]}")


async def deploy():
    """Deploy the flow to the work pool."""
    deployment_id = await failing_flow.deploy(
        name="test-force-reschedule-20108",
        work_pool_name=WORK_POOL,
        work_queue_name=WORK_QUEUE,
        build=False,
        push=False,
    )
    print(f"Deployed: {deployment_id}")


async def trigger():
    """Trigger a failing run."""
    async with get_client() as client:
        deployments = await client.read_deployments()
        deployment = next(
            (d for d in deployments if d.name == "test-force-reschedule-20108"),
            None,
        )
        if not deployment:
            print("Deployment not found. Run with 'deploy' first.")
            return

        flow_run = await client.create_flow_run_from_deployment(
            deployment_id=deployment.id,
        )
        print(f"Triggered flow run: {flow_run.id}")
        print(f"  work_queue_id: {flow_run.work_queue_id}")
        print("\nRun a worker to execute this, then use 'reschedule <flow_run_id>'")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python repros/20108.py deploy      # Deploy the flow")
        print("  python repros/20108.py trigger     # Trigger a run")
        print("  python repros/20108.py reschedule <flow_run_id>  # Force reschedule")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "deploy":
        asyncio.run(deploy())
    elif cmd == "trigger":
        asyncio.run(trigger())
    elif cmd == "reschedule":
        if len(sys.argv) < 3:
            print("Usage: python repros/20108.py reschedule <flow_run_id>")
            sys.exit(1)
        asyncio.run(force_reschedule(sys.argv[2]))
