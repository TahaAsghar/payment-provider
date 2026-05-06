from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from app.helpers.enums import PaymentStatus, RefundStatus
from app.schemas import NormalizedPaymentResponse, NormalizedRefundResponse
from app.helpers.enums import ProviderName
from app.interface.provider_interface import PaymentProviderInterface
from app.services.provider_registry import register_provider

logger = logging.getLogger(__name__)


_PAYMENT_STATUS_MAP: dict[str, PaymentStatus] = {
    "created": PaymentStatus.PENDING,
    "pending": PaymentStatus.PENDING,
    "completed": PaymentStatus.SUCCESS,
    "succeeded": PaymentStatus.SUCCESS,
    "failed": PaymentStatus.FAILED,
    "cancelled": PaymentStatus.CANCELLED,
    "refunded": PaymentStatus.REFUNDED,
}

_REFUND_STATUS_MAP: dict[str, RefundStatus] = {
    "created": RefundStatus.PENDING,
    "pending": RefundStatus.PENDING,
    "completed": RefundStatus.SUCCESS,
    "succeeded": RefundStatus.SUCCESS,
    "failed": RefundStatus.FAILED,
}


@register_provider(ProviderName.PROVIDER_A)
class ProviderAAdapter(PaymentProviderInterface):

    @staticmethod
    def _normalize_status(raw_state: str) -> PaymentStatus:
        return _PAYMENT_STATUS_MAP.get(
            raw_state.lower(), PaymentStatus.PENDING
        )

    @staticmethod
    def _normalize_refund_status(raw_state: str) -> RefundStatus:
        return _REFUND_STATUS_MAP.get(
            raw_state.lower(), RefundStatus.PENDING
        )


    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
    ) -> NormalizedPaymentResponse:

        amount_minor = int(amount * 100)

        payload = {
            "amount": amount_minor,
            "currency": currency,
            "customer_id": customer_id,
        }

        logger.info("Provider A — creating payment: %s", payload)

        raw: dict = {
            "id": f"pay_A_{uuid.uuid4().hex[:8]}",
            "state": "created",
            "amount": amount_minor,
            "currency": currency,
        }

        return NormalizedPaymentResponse(
            provider_reference=raw["id"],
            status=self._normalize_status(raw["state"]),
            amount=Decimal(raw["amount"]) / 100,  # convert minor → major
            currency=raw["currency"],
            raw_response=raw,
        )

    async def refund_payment(
        self,
        provider_reference: str,
        amount: Decimal,
        reason: str,
    ) -> NormalizedRefundResponse:
        amount_minor = int(amount * 100)

        logger.info(
            "Provider A — refunding %s (amount=%d, reason=%s)",
            provider_reference,
            amount_minor,
            reason,
        )

        raw: dict = {
            "id": f"ref_A_{uuid.uuid4().hex[:8]}",
            "state": "created",
            "amount": amount_minor,
            "original_payment": provider_reference,
        }

        return NormalizedRefundResponse(
            provider_reference=raw["id"],
            status=self._normalize_refund_status(raw["state"]),
            refunded_amount=Decimal(raw["amount"]) / 100,
            raw_response=raw,
        )
