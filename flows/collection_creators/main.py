"""who created records of a given atproto collection, and how many.

uses microcosm.blue infra:
- lightrail enumerates DIDs that have ever held records of a collection
- slingshot resolves each DID to its PDS endpoint
- the PDS itself answers com.atproto.repo.listRecords for the count
"""

from collections.abc import Iterator
from typing import NamedTuple

import httpx
from prefect import flow, task

LIGHTRAIL = "https://lightrail.microcosm.blue"
SLINGSHOT = "https://slingshot.microcosm.blue"


class ResolvedDid(NamedTuple):
    did: str
    handle: str
    pds: str


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
def discover_creator_dids(collection: str, page_size: int = 1000) -> list[str]:
    with httpx.Client(timeout=30.0) as client:
        dids = list(_iter_creator_dids(client, collection, page_size))
    print(f"lightrail found {len(dids)} creators of {collection}")
    return dids


@task(retries=2, retry_delay_seconds=2, log_prints=True)
def resolve_pds(did: str) -> ResolvedDid:
    with httpx.Client(timeout=15.0) as client:
        r = client.get(
            f"{SLINGSHOT}/xrpc/blue.microcosm.identity.resolveMiniDoc",
            params={"identifier": did},
        )
        r.raise_for_status()
        doc = r.json()
    return ResolvedDid(did=did, handle=doc.get("handle") or did, pds=doc["pds"])


@task(retries=2, retry_delay_seconds=2, log_prints=True)
def count_records(pds: str, did: str, collection: str) -> int | None:
    """paginate listRecords on the user's PDS and return the total count.

    returns None if the PDS is unreachable (e.g. cert chain issues on
    self-hosted instances) so the rest of the fan-out can still complete.
    """
    total = 0
    cursor: str | None = None
    seen_cursors: set[str] = set()
    try:
        with httpx.Client(timeout=30.0, base_url=pds) as client:
            while True:
                params: dict[str, str | int] = {
                    "repo": did,
                    "collection": collection,
                    "limit": 100,
                }
                if cursor:
                    params["cursor"] = cursor
                r = client.get("/xrpc/com.atproto.repo.listRecords", params=params)
                r.raise_for_status()
                body = r.json()
                records = body.get("records", [])
                total += len(records)
                next_cursor = body.get("cursor")
                # some PDSes echo a stable cursor when there's nothing more; bail on
                # empty page or repeated cursor.
                if not records or not next_cursor or next_cursor in seen_cursors:
                    return total
                seen_cursors.add(next_cursor)
                cursor = next_cursor
    except httpx.HTTPError as exc:
        print(f"could not count {did} on {pds}: {exc!r}")
        return None


@flow(log_prints=True)
def creators_of_collection(
    collection: str = "tech.waow.ken.profile",
) -> dict[str, int]:
    """return {handle: record_count} for every creator of `collection`, sorted desc."""
    dids = discover_creator_dids(collection)
    if not dids:
        print(f"no creators found for collection {collection!r}")
        return {}

    resolved: list[ResolvedDid] = resolve_pds.map(dids).result()
    counts: list[int | None] = count_records.map(
        pds=[r.pds for r in resolved],
        did=[r.did for r in resolved],
        collection=collection,
    ).result()

    by_handle = {r.handle: n for r, n in zip(resolved, counts)}
    unreachable = [h for h, n in by_handle.items() if n is None]
    counted = {h: n for h, n in by_handle.items() if n is not None}
    ranked = dict(sorted(counted.items(), key=lambda kv: kv[1], reverse=True))

    total_records = sum(ranked.values())
    print(
        f"{len(ranked)} creators of {collection} hold {total_records} records total"
        + (f"  ({len(unreachable)} PDS unreachable)" if unreachable else "")
    )
    width = max((len(h) for h in ranked), default=0)
    for handle, n in ranked.items():
        print(f"  {handle:<{width}}  {n}")
    for handle in unreachable:
        print(f"  {handle:<{width}}  ? (unreachable)")
    return ranked


if __name__ == "__main__":
    creators_of_collection()
