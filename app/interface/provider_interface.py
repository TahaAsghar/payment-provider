"""
Outbound port — payment provider gateway
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from app.schemas import (
    NormalizedPaymentResponse,
    NormalizedRefundResponse,
)


class PaymentProviderInterface(ABC):

    @abstractmethod
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
    ) -> NormalizedPaymentResponse:
        ...

    @abstractmethod
    async def refund_payment(
        self,
        provider_reference: str,
        amount: Decimal,
        reason: str,
    ) -> NormalizedRefundResponse:
        ...
