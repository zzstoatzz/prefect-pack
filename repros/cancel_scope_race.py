"""
Repro for CancelScope race condition in Runner via ProcessWorker.

BUG SUMMARY:
When multiple flow runs are submitted concurrently to a ProcessWorker,
there's a race condition in Runner.__aenter__ where multiple tasks can try to
enter the same _runs_task_group CancelScope.

ERROR: RuntimeError("Each CancelScope may only be used for a single 'with' block")

LOCATION: src/prefect/runner/runner.py:1582-1584

Run with: uv run python repros/cancel_scope_race.py

Requires a local Prefect server running (prefect server start) or staging.
"""

import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID

# Suppress noisy logs before imports
logging.getLogger("prefect").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.CRITICAL)

from prefect import flow
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterState,
    FlowRunFilterStateType,
)
from prefect.workers.process import ProcessWorker


@flow
def dummy_flow(x: int = 0):
    """Simple flow that completes quickly."""
    return x


async def deploy_flow(work_pool: str) -> UUID:
    """Deploy the flow and return deployment ID."""
    runnable = await dummy_flow.from_source(
        source=str(Path(__file__).parent),
        entrypoint="cancel_scope_race.py:dummy_flow",
    )
    deployment_id = await runnable.deploy(
        name="cancel-scope-repro",
        work_pool_name=work_pool,
        build=False,
        push=False,
    )
    return deployment_id


async def create_flow_runs(deployment_id: UUID, count: int) -> list[UUID]:
    """Create scheduled flow runs from deployment."""
    async with get_client() as client:
        tasks = [
            client.create_flow_run_from_deployment(
                deployment_id=deployment_id,
                parameters={"x": i},
            )
            for i in range(count)
        ]
        flow_runs = await asyncio.gather(*tasks)
        return [fr.id for fr in flow_runs]


async def check_for_cancel_scope_crashes() -> int:
    """Check for flow runs that crashed with CancelScope error."""
    async with get_client() as client:
        crashed_runs = await client.read_flow_runs(
            flow_run_filter=FlowRunFilter(
                state=FlowRunFilterState(type=FlowRunFilterStateType(any_=["CRASHED"]))
            ),
            limit=100,
        )
        count = 0
        for run in crashed_runs:
            if run.state and run.state.message and "CancelScope" in run.state.message:
                count += 1
                print(f"    FOUND: {run.id} - {run.state.message[:80]}...")
        return count


async def run_test(
    work_pool: str, deployment_id: UUID, num_runs: int
) -> tuple[int, int]:
    """Run a single test iteration. Returns (submitted, cancel_scope_errors)."""

    print(f"  Creating {num_runs} flow runs...")
    flow_run_ids = await create_flow_runs(deployment_id, num_runs)
    print(f"  Created {len(flow_run_ids)} flow runs")

    # Use ProcessWorker with high concurrency limit
    worker = ProcessWorker(
        work_pool_name=work_pool,
        limit=50,
    )

    cancel_scope_errors = 0
    submitted = 0

    try:
        async with worker:
            print("  Getting and submitting flow runs...")
            results = await worker.get_and_submit_flow_runs()
            submitted = len(results)
            print(f"  Submitted {submitted} flow runs")

            # Wait for runs to complete/fail
            await asyncio.sleep(5)

    except Exception as e:
        if "CancelScope" in str(e):
            print(f"  CAUGHT CancelScope error: {e}")
            cancel_scope_errors += 1
        else:
            print(f"  Error: {type(e).__name__}: {str(e)[:100]}")

    return submitted, cancel_scope_errors


async def main():
    work_pool = "test-cancel-scope"
    num_runs = 20
    num_iterations = 3

    print("CancelScope Race Condition Repro")
    print("=" * 50)
    print(f"Work pool: {work_pool}")
    print(f"Concurrent flow runs: {num_runs}")
    print()

    # Ensure work pool exists
    async with get_client() as client:
        try:
            await client.read_work_pool(work_pool)
            print(f"Using existing work pool: {work_pool}")
        except Exception:
            from prefect.client.schemas.actions import WorkPoolCreate

            await client.create_work_pool(
                work_pool=WorkPoolCreate(name=work_pool, type="process")
            )
            print(f"Created work pool: {work_pool}")

    # Deploy the flow
    print("Deploying flow...")
    deployment_id = await deploy_flow(work_pool)
    print(f"Deployment ID: {deployment_id}")
    print()

    total_submitted = 0
    total_errors = 0

    for i in range(num_iterations):
        print(f"--- Iteration {i + 1}/{num_iterations} ---")
        submitted, errors = await run_test(work_pool, deployment_id, num_runs)
        total_submitted += submitted
        total_errors += errors

        # Check for crashed runs with CancelScope
        crashed_with_cancel = await check_for_cancel_scope_crashes()
        total_errors += crashed_with_cancel

        print()
        await asyncio.sleep(1)

    print("=" * 50)
    print("RESULTS:")
    print(f"  Total submitted: {total_submitted}")
    print(f"  CancelScope errors: {total_errors}")

    if total_errors > 0:
        print("\nBUG CONFIRMED: CancelScope race condition exists.")
        print("See src/prefect/runner/runner.py:1582-1584")
        return 1
    else:
        print("\nNo CancelScope errors this run.")
        print("Race is probabilistic - try increasing num_runs or iterations.")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
