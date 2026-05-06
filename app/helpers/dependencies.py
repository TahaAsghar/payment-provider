from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.payment_repository import PaymentRepository
from app.interface.repository_interface import PaymentRepositoryInterface
from app.database import get_async_session
from app.models import IdempotencyLogORM
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

async def get_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PaymentRepositoryInterface:
    return PaymentRepository(session)


async def get_payment_service(
    repo: PaymentRepositoryInterface = Depends(get_repository),
) -> PaymentService:
    return PaymentService(repository=repo)

class IdempotencyResult:

    def __init__(
        self,
        *,
        is_duplicate: bool,
        previous_response: Optional[dict[str, Any]] = None,
        previous_status_code: int = 200,
        idempotency_key: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        self.is_duplicate = is_duplicate
        self.previous_response = previous_response
        self.previous_status_code = previous_status_code
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
    """
    if idempotency_key is None:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required for this endpoint.",
        )

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
                is_duplicate=True,
                previous_response=existing.response_body,
                previous_status_code=existing.response_code or 200,
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
        is_duplicate=False,
        idempotency_key=idempotency_key,
        session=session,
    )
