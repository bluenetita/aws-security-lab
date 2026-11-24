"""Read-only REST API for imported Zeek connections."""

import logging

from ipaddress import ip_address
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from .zeek import ZeekConnectionPage, get_zeek_snapshot


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/zeek",
    tags=["zeek"]
)


@router.get(
    "/connections",
    response_model=ZeekConnectionPage
)
def list_connections(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    source_ip: Annotated[
        str | None, Query(max_length=45)
    ] = None,
    proto: Annotated[
        str | None,
        Query(pattern="^(tcp|udp|icmp)$")
    ] = None,
):
    try:
        items = list(get_zeek_snapshot())

    except (OSError, ValueError) as exc:
        logger.error(
            "Zeek snapshot unavailable: %s",
            type(exc).__name__
        )
        raise HTTPException(
            status_code=503,
            detail="Zeek snapshot unavailable"
        ) from exc

    if source_ip is not None:
        try:
            address = ip_address(source_ip)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="Invalid source_ip"
            ) from exc

        items = [
            item for item in items
            if item.source_ip == address
        ]

    if proto is not None:
        items = [
            item for item in items
            if item.proto == proto
        ]

    return ZeekConnectionPage(
        total=len(items),
        limit=limit,
        offset=offset,
        items=items[offset:offset + limit]
    )
