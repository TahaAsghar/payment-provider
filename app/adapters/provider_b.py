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
    "initiated": PaymentStatus.PENDING,
    "pending": PaymentStatus.PENDING,
    "captured": PaymentStatus.SUCCESS,
    "completed": PaymentStatus.SUCCESS,
    "declined": PaymentStatus.FAILED,
    "failed": PaymentStatus.FAILED,
    "voided": PaymentStatus.CANCELLED,
    "refunded": PaymentStatus.REFUNDED,
}

_REFUND_STATUS_MAP: dict[str, RefundStatus] = {
    "initiated": RefundStatus.PENDING,
    "pending": RefundStatus.PENDING,
    "completed": RefundStatus.SUCCESS,
    "settled": RefundStatus.SUCCESS,
    "failed": RefundStatus.FAILED,
}


@register_provider(ProviderName.PROVIDER_B)
class ProviderBAdapter(PaymentProviderInterface):

    @staticmethod
    def _normalize_status(raw_status: str) -> PaymentStatus:
        return _PAYMENT_STATUS_MAP.get(
            raw_status.strip().lower(), PaymentStatus.PENDING
        )

    @staticmethod
    def _normalize_refund_status(raw_status: str) -> RefundStatus:
        return _REFUND_STATUS_MAP.get(
            raw_status.strip().lower(), RefundStatus.PENDING
        )


    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
    ) -> NormalizedPaymentResponse:

        payload = {
            "totalAmount": str(amount),
            "currencyCode": currency,
            "customerId": customer_id,
        }

        logger.info("Provider B — creating payment: %s", payload)

        raw: dict = {
            "transactionId": f"txn_B_{uuid.uuid4().hex[:8]}",
            "paymentStatus": "INITIATED",
            "totalAmount": str(amount),
            "currencyCode": currency,
        }

        return NormalizedPaymentResponse(
            provider_reference=raw["transactionId"],
            status=self._normalize_status(raw["paymentStatus"]),
            amount=Decimal(raw["totalAmount"]),
            currency=raw["currencyCode"],
            raw_response=raw,
        )

    async def refund_payment(
        self,
        provider_reference: str,
        amount: Decimal,
        reason: str,
    ) -> NormalizedRefundResponse:
        logger.info(
            "Provider B — refunding %s (amount=%s, reason=%s)",
            provider_reference,
            amount,
            reason,
        )

        raw: dict = {
            "transactionId": f"ref_B_{uuid.uuid4().hex[:8]}",
            "paymentStatus": "INITIATED",
            "totalAmount": str(amount),
            "originalTransaction": provider_reference,
        }

        return NormalizedRefundResponse(
            provider_reference=raw["transactionId"],
            status=self._normalize_refund_status(raw["paymentStatus"]),
            refunded_amount=Decimal(raw["totalAmount"]),
            raw_response=raw,
        )
