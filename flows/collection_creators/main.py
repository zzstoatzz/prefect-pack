# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "prefect",
#     "atproto @ git+https://github.com/zzstoatzz/atproto.git@v0.0.66",
# ]
# ///
"""who created records of a given atproto collection, and how many.

pipeline:
- ufos `/collections/stats` gives a fast network-wide preview (firehose-sampled
  totals — undercounts; CAR walks below produce ground truth)
- lightrail `listReposByCollection` enumerates the DIDs that hold records of
  the collection
- slingshot `resolveMiniDoc` maps each DID to its PDS endpoint
- `com.atproto.sync.getRepo` pulls the full repo as a CAR file; we walk the
  MST locally and count keys with the target collection prefix. one HTTP
  call per creator replaces paginated `listRecords` (which is ~1000
  round-trips for a 100k-record user).

note: the atproto python SDK gives us CAR parsing but no MST walker — that
part is ours, ~10 lines.

the batched task is cached (cache_policy = INPUTS - "max_in_flight",
cache_expiration = 1h) and tagged "atproto-pds"; create a tag limit to
rate-limit concurrent batches across flow runs:
    prefect concurrency-limit create atproto-pds 1

run from anywhere with uv (defaults to tech.waow.ken.profile):
  uv run https://raw.githubusercontent.com/zzstoatzz/prefect-pack/main/flows/collection_creators/main.py

  uv run https://raw.githubusercontent.com/zzstoatzz/prefect-pack/main/flows/collection_creators/main.py <some.nsid>
"""

import asyncio
import sys
from collections.abc import Iterator
from datetime import timedelta
from typing import NamedTuple

import httpx
from atproto_core.car import CAR
from atproto_core.cid import CID
from prefect import flow, task
from prefect.cache_policies import INPUTS

LIGHTRAIL = "https://lightrail.microcosm.blue"
SLINGSHOT = "https://slingshot.microcosm.blue"
UFOS = "https://ufos-api.microcosm.blue"


class CreatorStat(NamedTuple):
    """per-DID result. `count` is None if we couldn't fetch+walk the repo;
    `error` says why ("unresolved" = slingshot couldn't resolve the DID,
    "unreachable" = PDS rejected getRepo or returned garbage)."""

    handle: str
    count: int | None
    error: str | None


def _iter_creator_dids(
    client: httpx.Client, collection: str, page_size: int
) -> Iterator[str]:
    cursor: str | None = None
    while True:
        params: dict[str, str | int] = {"collection": collection, "limit": page_size}
        if cursor:
            params["cursor"] = cursor
        r = client.get(
            f"{LIGHTRAIL}/xrpc/com.atproto.sync.listReposByCollection", params=params
        )
        r.raise_for_status()
        body = r.json()
        for repo in body.get("repos", []):
            yield repo["did"]
        cursor = body.get("cursor")
        if not cursor:
            return


@task(log_prints=True)
def preview_collection(collection: str) -> None:
    """ask ufos for the network-wide totals so users see scale before the long work."""
    try:
        r = httpx.get(
            f"{UFOS}/collections/stats",
            params={"collection": collection},
            timeout=10.0,
        )
        r.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"ufos preview unavailable: {exc!r}")
        return
    if not (stats := r.json().get(collection)):
        return
    net = stats["creates"] - stats["deletes"]
    print(
        f"ufos: {collection} has ~{net:,} live records "
        f"({stats['creates']:,} creates / {stats['deletes']:,} deletes) "
        f"across ~{stats['dids_estimate']:,} DIDs "
        f"(network-wide, firehose-sampled — CAR walks below are ground truth)"
    )


@task(log_prints=True)
def discover_creator_dids(collection: str, page_size: int = 1000) -> list[str]:
    with httpx.Client(timeout=30.0) as client:
        dids = sorted(_iter_creator_dids(client, collection, page_size))
    # sorted so the cache key for gather_creator_stats is stable across
    # flow runs (lightrail makes no ordering guarantee).
    print(f"lightrail enumerated {len(dids):,} creators of {collection}")
    return dids


async def _resolve_one(client: httpx.AsyncClient, did: str) -> tuple[str, str] | None:
    try:
        r = await client.get(
            f"{SLINGSHOT}/xrpc/blue.microcosm.identity.resolveMiniDoc",
            params={"identifier": did},
        )
        r.raise_for_status()
        doc = r.json()
    except httpx.HTTPError:
        return None
    return doc.get("handle") or did, doc["pds"]


def _count_in_car(car_bytes: bytes, collection: str) -> int:
    """walk the MST and count keys with prefix '{collection}/'.

    MST keys are "{collection}/{rkey}" — counting is a tree walk with no
    record-value decode. linear in repo size, dominated by the http fetch.

    note: CAR.blocks is keyed by CID objects, but CIDs appearing inside
    decoded DAG-CBOR values come through as raw bytes — CID.decode(...)
    bridges the two.
    """
    car = CAR.from_bytes(car_bytes)
    blocks = car.blocks
    data_cid = CID.decode(blocks[car.root]["data"])

    prefix = f"{collection}/".encode()
    count = 0
    stack = [data_cid]
    while stack:
        node = blocks[stack.pop()]
        if (left := node.get("l")) is not None:
            stack.append(CID.decode(left))
        prev_key = b""
        for entry in node["e"]:
            key = prev_key[: entry["p"]] + entry["k"]
            prev_key = key
            if key.startswith(prefix):
                count += 1
            if (t := entry.get("t")) is not None:
                stack.append(CID.decode(t))
    return count


async def _count_one(
    client: httpx.AsyncClient, pds: str, did: str, collection: str
) -> int | None:
    """getRepo → CAR → MST walk → count for `collection`. None on failure."""
    try:
        r = await client.get(
            f"{pds}/xrpc/com.atproto.sync.getRepo", params={"did": did}
        )
        r.raise_for_status()
        return _count_in_car(r.content, collection)
    except (httpx.HTTPError, KeyError, ValueError):
        return None


async def _gather_stats(
    dids: list[str], collection: str, max_in_flight: int
) -> list[CreatorStat]:
    sem = asyncio.Semaphore(max_in_flight)
    done = 0
    total = len(dids)
    started_at = asyncio.get_event_loop().time()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
        limits=httpx.Limits(
            max_connections=max_in_flight * 2, max_keepalive_connections=max_in_flight
        ),
        follow_redirects=True,
    ) as client:

        async def work(did: str) -> CreatorStat:
            nonlocal done
            async with sem:
                if (resolved := await _resolve_one(client, did)) is None:
                    result = CreatorStat(handle=did, count=None, error="unresolved")
                else:
                    handle, pds = resolved
                    count = await _count_one(client, pds, did, collection)
                    result = (
                        CreatorStat(handle=handle, count=count, error=None)
                        if count is not None
                        else CreatorStat(handle=handle, count=None, error="unreachable")
                    )
            done += 1
            elapsed = asyncio.get_event_loop().time() - started_at
            shown = result.count if result.count is not None else f"({result.error})"
            print(
                f"  [{done:>4}/{total}] {result.handle:<35} "
                f"= {shown:>8}  ({elapsed:5.1f}s elapsed)"
            )
            return result

        return await asyncio.gather(*(work(d) for d in dids))


@task(
    log_prints=True,
    tags=["atproto-pds"],
    cache_policy=INPUTS - "max_in_flight",
    cache_expiration=timedelta(hours=1),
    persist_result=True,
)
def gather_creator_stats(
    dids: list[str], collection: str, max_in_flight: int = 50
) -> list[CreatorStat]:
    """resolve + count for every DID via getRepo CAR walk.

    cache_policy=INPUTS - "max_in_flight" so the cache key is (dids, collection):
    max_in_flight only affects how the work runs, not the output, so excluding
    it from the key means a faster machine can still re-use slower runs'
    results. cache_expiration=1h. results are persisted under
    ~/.prefect/storage so hits survive process restarts.
    """
    return asyncio.run(_gather_stats(dids, collection, max_in_flight))


@flow(log_prints=True)
def creators_of_collection(
    collection: str = "tech.waow.ken.profile",
    max_in_flight: int = 50,
) -> dict[str, int]:
    """return {handle: record_count} for every creator of `collection`, sorted desc."""
    preview_collection(collection)
    dids = discover_creator_dids(collection)
    if not dids:
        print(f"no creators found for collection {collection!r}")
        return {}

    stats = gather_creator_stats(dids, collection, max_in_flight=max_in_flight)

    counted = {s.handle: s.count for s in stats if s.count is not None}
    unresolved = sum(1 for s in stats if s.error == "unresolved")
    unreachable = [s.handle for s in stats if s.error == "unreachable"]
    ranked = dict(sorted(counted.items(), key=lambda kv: kv[1], reverse=True))

    issues: list[str] = []
    if unresolved:
        issues.append(f"{unresolved} DID unresolved")
    if unreachable:
        issues.append(f"{len(unreachable)} PDS unreachable")
    total_records = sum(ranked.values())
    holders = sum(1 for n in ranked.values() if n > 0)
    print(
        f"{holders} of {len(ranked)} reachable creators hold "
        f"{total_records:,} {collection} records"
        + (f"  ({', '.join(issues)})" if issues else "")
    )
    width = max((len(h) for h in ranked), default=0)
    for handle, n in ranked.items():
        if n > 0:
            print(f"  {handle:<{width}}  {n:,}")
    for handle in unreachable:
        print(f"  {handle:<{width}}  ? (unreachable)")
    return ranked


if __name__ == "__main__":
    collection = sys.argv[1] if len(sys.argv) > 1 else "tech.waow.ken.profile"
    creators_of_collection(collection)
