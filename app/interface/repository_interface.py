"""
Outbound port — persistence
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Optional

from app.helpers.enums import PaymentStatus, ProviderName, RefundStatus
from app.schemas import (
    PaymentDetail,
    RefundDetail,
)


class PaymentRepositoryInterface(ABC):
 
    @abstractmethod
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
        ...

    @abstractmethod
    async def get_payment(self, payment_id: uuid.UUID) -> Optional[PaymentDetail]:
        ...

    @abstractmethod
    async def get_payment_for_update(self, payment_id: uuid.UUID) -> Optional[PaymentDetail]:
        ...

    @abstractmethod
    async def update_payment_status(
        self,
        payment_id: uuid.UUID,
        *,
        status: PaymentStatus,
        provider_reference: Optional[str] = None,
        raw_response: Optional[dict[str, Any]] = None,
    ) -> PaymentDetail:
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def get_refunds_for_payment(
        self, payment_id: uuid.UUID
    ) -> list[RefundDetail]:
        ...
