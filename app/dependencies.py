"""
FastAPI dependencies — idempotency interceptor, session injection,
and service wiring.

The idempotency layer uses a DB-backed log with row-level locking
(SELECT … FOR UPDATE) to prevent duplicate processing of the same
request.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.payment_repository import PaymentRepository
from app.domain.repository_port import PaymentRepositoryInterface
from app.infrastructure.database import get_async_session
from app.models import IdempotencyLogORM
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session → Repository → Service dependency chain
# ---------------------------------------------------------------------------


async def get_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PaymentRepositoryInterface:
    return PaymentRepository(session)


async def get_payment_service(
    repo: PaymentRepositoryInterface = Depends(get_repository),
) -> PaymentService:
    return PaymentService(repository=repo)


# ---------------------------------------------------------------------------
# Idempotency interceptor
# ---------------------------------------------------------------------------


class IdempotencyResult:
    """
    Carries either a cached response (already completed) or a freshly
    acquired lock row so the endpoint can proceed and mark it done.
    """

    def __init__(
        self,
        *,
        is_cached: bool,
        cached_response: Optional[dict[str, Any]] = None,
        cached_status_code: int = 200,
        idempotency_key: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        self.is_cached = is_cached
        self.cached_response = cached_response
        self.cached_status_code = cached_status_code
        self.idempotency_key = idempotency_key
        self.session = session

    async def mark_completed(
        self, response_code: int, response_body: dict[str, Any]
    ) -> None:
        """Persist the final response so future duplicate calls return it."""
        if self.session is None or self.idempotency_key is None:
            return

        stmt = (
            select(IdempotencyLogORM)
            .where(IdempotencyLogORM.idempotency_key == self.idempotency_key)
        )
        result = await self.session.execute(stmt)
        log = result.scalar_one_or_none()
        if log is not None:
            log.status = "COMPLETED"
            log.response_code = response_code
            log.response_body = response_body
            await self.session.flush()


async def idempotency_guard(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> IdempotencyResult:
    """
    FastAPI dependency that enforces idempotency on POST endpoints.

    Algorithm:
      1. If no Idempotency-Key header → proceed normally (no guard).
      2. SELECT FOR UPDATE on the key to acquire a row-level lock.
      3. If the row exists and is COMPLETED → return the cached response.
      4. If the row exists but is IN_PROGRESS → raise 409 (concurrent dup).
      5. If no row → INSERT an IN_PROGRESS record and let the request proceed.
    """
    if idempotency_key is None:
        return IdempotencyResult(is_cached=False, session=session)

    endpoint = f"{request.method} {request.url.path}"

    # Row-level lock — prevents race conditions between concurrent
    # requests bearing the same key.
    stmt = (
        select(IdempotencyLogORM)
        .where(IdempotencyLogORM.idempotency_key == idempotency_key)
        .with_for_update()
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        if existing.status == "COMPLETED":
            logger.info("Idempotency HIT for key=%s", idempotency_key)
            return IdempotencyResult(
                is_cached=True,
                cached_response=existing.response_body,
                cached_status_code=existing.response_code or 200,
            )
        # Still in progress — another request is handling it right now.
        raise HTTPException(
            status_code=409,
            detail="A request with this Idempotency-Key is already being processed.",
        )

    # First time — create IN_PROGRESS record.
    new_log = IdempotencyLogORM(
        idempotency_key=idempotency_key,
        endpoint=endpoint,
        status="IN_PROGRESS",
    )
    session.add(new_log)
    await session.flush()
    logger.info("Idempotency MISS — created IN_PROGRESS for key=%s", idempotency_key)

    return IdempotencyResult(
        is_cached=False,
        idempotency_key=idempotency_key,
        session=session,
    )
