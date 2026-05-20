# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "prefect",
#     "atproto @ git+https://github.com/zzstoatzz/atproto.git@v0.0.1",
# ]
# ///
"""who created records of a given atproto collection, and how many.

pipeline:
- ufos `/collections/stats` gives a fast network-wide preview (firehose-sampled
  totals — undercounts; CAR walks below produce ground truth)
- lightrail `listReposByCollection` enumerates the DIDs that hold records of
  the collection
- slingshot `resolveMiniDoc` maps each DID to its PDS endpoint
- `com.atproto.sync.getRepo` pulls the full repo as a CAR file; one walk of
  the MST yields exact counts for *every* collection in the repo (the MST
  keys are "{collection}/{rkey}" strings — no record-value decode needed)

the per-DID work returns dict[collection, int] — counting one collection is
the same walk as counting all of them. the cached batched task stores the
full breakdown per DID and is keyed only on the DID list, so re-running the
flow for a different collection (same DIDs) is a cache hit: the filter
happens after the fetch, not inside it.

the batched task carries an "atproto-pds" tag; create a tag-level limit to
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


class CreatorBreakdown(NamedTuple):
    """per-DID result. `counts` is None if we couldn't fetch+walk the repo;
    `error` says why ("unresolved" = slingshot couldn't resolve the DID,
    "unreachable" = PDS rejected getRepo or returned garbage)."""

    handle: str
    counts: dict[str, int] | None
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
        stats = r.json().get(collection)
    except httpx.HTTPError as exc:
        print(f"ufos preview unavailable: {exc!r}")
        return
    if not stats:
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
    # sorted so the cache key for gather_creator_breakdowns is stable across
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


def _count_all_collections(car_bytes: bytes) -> dict[str, int]:
    """walk the MST and tally records per collection in a single pass.

    MST keys are "{collection}/{rkey}" — counting one collection vs all of
    them is the same walk. counting all of them once and filtering downstream
    means "re-run with a different collection on the same DIDs" is a cache
    hit, not a re-fetch of every CAR.

    note: CAR.blocks is keyed by CID objects, but CIDs appearing inside
    decoded DAG-CBOR values come through as raw bytes — CID.decode(...)
    bridges the two.
    """
    car = CAR.from_bytes(car_bytes)
    blocks = car.blocks
    data_cid = CID.decode(blocks[car.root]["data"])

    counts: dict[str, int] = {}
    stack = [data_cid]
    while stack:
        node = blocks[stack.pop()]
        left = node.get("l")
        if left is not None:
            stack.append(CID.decode(left))
        prev_key = b""
        for entry in node["e"]:
            key = prev_key[: entry["p"]] + entry["k"]
            prev_key = key
            slash = key.find(b"/")
            if slash > 0:
                collection_name = key[:slash].decode("ascii", errors="replace")
                counts[collection_name] = counts.get(collection_name, 0) + 1
            t = entry.get("t")
            if t is not None:
                stack.append(CID.decode(t))
    return counts


async def _walk_repo(
    client: httpx.AsyncClient, pds: str, did: str
) -> dict[str, int] | None:
    """getRepo → CAR → MST walk → per-collection counts. None on failure."""
    try:
        r = await client.get(
            f"{pds}/xrpc/com.atproto.sync.getRepo", params={"did": did}
        )
        r.raise_for_status()
        return _count_all_collections(r.content)
    except (httpx.HTTPError, KeyError, ValueError):
        return None


async def _gather_breakdowns(
    dids: list[str], max_in_flight: int
) -> list[CreatorBreakdown]:
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

        async def work(did: str) -> CreatorBreakdown:
            nonlocal done
            async with sem:
                resolved = await _resolve_one(client, did)
                if resolved is None:
                    result = CreatorBreakdown(
                        handle=did, counts=None, error="unresolved"
                    )
                else:
                    handle, pds = resolved
                    counts = await _walk_repo(client, pds, did)
                    if counts is None:
                        result = CreatorBreakdown(
                            handle=handle, counts=None, error="unreachable"
                        )
                    else:
                        result = CreatorBreakdown(
                            handle=handle, counts=counts, error=None
                        )
            done += 1
            elapsed = asyncio.get_event_loop().time() - started_at
            collections_str = (
                f"{len(result.counts):>3} collections"
                if result.counts is not None
                else f"({result.error})"
            )
            print(
                f"  [{done:>4}/{total}] {result.handle:<35} {collections_str:>20}  ({elapsed:5.1f}s elapsed)"
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
def gather_creator_breakdowns(
    dids: list[str], max_in_flight: int = 50
) -> list[CreatorBreakdown]:
    """resolve + walk every creator's CAR, return per-collection counts per DID.

    cache_policy=INPUTS - "max_in_flight" so the cache key is just the DID
    list. max_in_flight only affects how the work runs, not the output, so
    excluding it from the key means a faster machine can still re-use slower
    runs' results. cache_expiration=1h.

    NOT keyed on any target collection — the result is the full per-collection
    breakdown per DID, so a later flow run filtering for a different NSID
    reuses the same fetch.
    """
    return asyncio.run(_gather_breakdowns(dids, max_in_flight))


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

    breakdowns = gather_creator_breakdowns(dids, max_in_flight=max_in_flight)

    counted: dict[str, int] = {}
    unresolved = 0
    unreachable: list[str] = []
    for b in breakdowns:
        if b.error == "unresolved":
            unresolved += 1
        elif b.error == "unreachable":
            unreachable.append(b.handle)
        elif b.counts is not None:
            # MST may not contain this collection at all → 0
            counted[b.handle] = b.counts.get(collection, 0)

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
