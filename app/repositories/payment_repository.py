from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import PaymentStatus, ProviderName, RefundStatus
from app.schemas import PaymentDetail, RefundDetail
from app.domain.repository_port import PaymentRepositoryInterface
from app.models import PaymentORM, RefundORM


class PaymentRepository(PaymentRepositoryInterface):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_payment(
        self,
        *,
        provider: ProviderName,
        amount: Decimal,
        currency: str,
        customer_id: str,
        status: PaymentStatus,
        provider_reference: Optional[str] = None,
        raw_response: Optional[dict[str, Any]] = None,
    ) -> PaymentDetail:
        now = datetime.now(timezone.utc)
        row = PaymentORM(
            id=uuid.uuid4(),
            provider=provider,
            provider_reference=provider_reference,
            amount=amount,
            currency=currency.upper(),
            customer_id=customer_id,
            status=status,
            raw_response=raw_response,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_payment_detail(row)

    async def get_payment(self, payment_id: uuid.UUID) -> Optional[PaymentDetail]:
        stmt = select(PaymentORM).where(PaymentORM.id == payment_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_payment_detail(row)

    async def update_payment_status(
        self,
        payment_id: uuid.UUID,
        *,
        status: PaymentStatus,
        provider_reference: Optional[str] = None,
        raw_response: Optional[dict[str, Any]] = None,
    ) -> PaymentDetail:
        values: dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if provider_reference is not None:
            values["provider_reference"] = provider_reference
        if raw_response is not None:
            values["raw_response"] = raw_response

        stmt = (
            update(PaymentORM)
            .where(PaymentORM.id == payment_id)
            .values(**values)
            .returning(PaymentORM)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one()
        return self._to_payment_detail(row)

    async def create_refund(
        self,
        *,
        payment_id: uuid.UUID,
        amount: Decimal,
        reason: str,
        status: RefundStatus,
        provider_reference: Optional[str] = None,
        raw_response: Optional[dict[str, Any]] = None,
    ) -> RefundDetail:
        row = RefundORM(
            id=uuid.uuid4(),
            payment_id=payment_id,
            provider_reference=provider_reference,
            amount=amount,
            reason=reason,
            status=status,
            raw_response=raw_response,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_refund_detail(row)

    async def get_refunds_for_payment(
        self, payment_id: uuid.UUID
    ) -> list[RefundDetail]:
        stmt = (
            select(RefundORM)
            .where(RefundORM.payment_id == payment_id)
            .order_by(RefundORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_refund_detail(r) for r in result.scalars().all()]

    @staticmethod
    def _to_payment_detail(row: PaymentORM) -> PaymentDetail:
        return PaymentDetail(
            id=row.id,
            provider=row.provider,
            provider_reference=row.provider_reference,
            amount=Decimal(str(row.amount)),
            currency=row.currency,
            customer_id=row.customer_id,
            status=row.status,
            raw_response=row.raw_response,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_refund_detail(row: RefundORM) -> RefundDetail:
        return RefundDetail(
            id=row.id,
            payment_id=row.payment_id,
            provider_reference=row.provider_reference,
            amount=Decimal(str(row.amount)),
            reason=row.reason,
            status=row.status,
            raw_response=row.raw_response,
            created_at=row.created_at,
        )
