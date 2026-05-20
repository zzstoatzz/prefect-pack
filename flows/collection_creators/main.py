# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "prefect",
#     "atproto @ git+https://github.com/zzstoatzz/atproto.git@v0.0.1",
# ]
# ///
"""who created records of a given atproto collection, and how many.

uses microcosm.blue infra:
- ufos gives a fast network-wide preview (total creates/deletes, dids estimate)
- lightrail enumerates the actual DIDs that have ever held records of a collection
- slingshot resolves each DID to its PDS endpoint

then per-DID counting via com.atproto.sync.getRepo: one HTTP GET returns the
entire repo as a CAR file (DAG-CBOR blocks + MST), and the MST keys are
"{collection}/{rkey}" strings — counting is a prefix-match traversal that
needs no record-value decoding. one HTTP call per creator replaces paginated
listRecords (which is ~1000 round-trips for a 100k-record user).

the work runs inside a single batched task, fanned out with asyncio.gather +
an in-process asyncio.Semaphore for HTTP concurrency. the batched task carries
an "atproto-pds" tag, so an optional tag-level concurrency limit can
rate-limit concurrent batches across flow runs.

to enable cross-run rate limiting, create a tag limit once on your server:
    prefect concurrency-limit create atproto-pds 1

run from anywhere with uv (defaults to tech.waow.ken.profile):
  uv run https://raw.githubusercontent.com/zzstoatzz/prefect-pack/main/flows/collection_creators/main.py

  uv run https://raw.githubusercontent.com/zzstoatzz/prefect-pack/main/flows/collection_creators/main.py <some.nsid>
"""

import asyncio
import sys
from collections.abc import Iterator
from typing import NamedTuple

import httpx
from atproto_core.car import CAR
from atproto_core.cid import CID
from prefect import flow, task

LIGHTRAIL = "https://lightrail.microcosm.blue"
SLINGSHOT = "https://slingshot.microcosm.blue"
UFOS = "https://ufos-api.microcosm.blue"


class CreatorStat(NamedTuple):
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
        f"across ~{stats['dids_estimate']:,} DIDs (network-wide estimate)"
    )


@task(log_prints=True)
def discover_creator_dids(collection: str, page_size: int = 1000) -> list[str]:
    with httpx.Client(timeout=30.0) as client:
        dids = list(_iter_creator_dids(client, collection, page_size))
    print(f"lightrail enumerated {len(dids):,} creators of {collection}")
    return dids


async def _resolve_one(
    client: httpx.AsyncClient, did: str
) -> tuple[str, str] | None:
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
    """count MST keys with prefix '{collection}/'.

    the entire repo arrives in one CAR; the SDK decodes blocks (DAG-CBOR
    dicts), the commit block points at the MST root, and MST keys are
    "{collection}/{rkey}" — so counting is a tree walk with no record-value
    decode. linear in repo size, dominated by the http fetch.

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
        left = node.get("l")
        if left is not None:
            stack.append(CID.decode(left))
        prev_key = b""
        for entry in node["e"]:
            key = prev_key[: entry["p"]] + entry["k"]
            prev_key = key
            if key.startswith(prefix):
                count += 1
            t = entry.get("t")
            if t is not None:
                stack.append(CID.decode(t))
    return count


async def _count_one(
    client: httpx.AsyncClient, pds: str, did: str, collection: str
) -> int | None:
    """fetch the repo CAR once and count `collection` records by walking the MST."""
    try:
        r = await client.get(
            f"{pds}/xrpc/com.atproto.sync.getRepo",
            params={"did": did},
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
                resolved = await _resolve_one(client, did)
                if resolved is None:
                    result = CreatorStat(handle=did, count=None, error="unresolved")
                else:
                    handle, pds = resolved
                    count = await _count_one(client, pds, did, collection)
                    if count is None:
                        result = CreatorStat(handle=handle, count=None, error="unreachable")
                    else:
                        result = CreatorStat(handle=handle, count=count, error=None)
            done += 1
            elapsed = asyncio.get_event_loop().time() - started_at
            print(
                f"  [{done:>4}/{total}] {result.handle:<35} "
                f"= {result.count if result.count is not None else f'({result.error})':>8}"
                f"  ({elapsed:5.1f}s elapsed)"
            )
            return result

        return await asyncio.gather(*(work(d) for d in dids))


@task(log_prints=True, tags=["atproto-pds"])
def gather_creator_stats(
    dids: list[str], collection: str, max_in_flight: int = 50
) -> list[CreatorStat]:
    """resolve + count every DID concurrently inside this task.

    in-process concurrency is bounded by asyncio.Semaphore(max_in_flight). the
    task itself carries the "atproto-pds" tag so a matching prefect GCL can
    rate-limit concurrent task runs across flow runs (one slot per task, not
    per HTTP request — the right granularity for orchestration-level limits).
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
    print(
        f"{len(ranked)} creators of {collection} hold {total_records:,} records total"
        + (f"  ({', '.join(issues)})" if issues else "")
    )
    width = max((len(h) for h in ranked), default=0)
    for handle, n in ranked.items():
        print(f"  {handle:<{width}}  {n:,}")
    for handle in unreachable:
        print(f"  {handle:<{width}}  ? (unreachable)")
    return ranked


if __name__ == "__main__":
    collection = sys.argv[1] if len(sys.argv) > 1 else "tech.waow.ken.profile"
    creators_of_collection(collection)
