"""
Provider A adapter — translates between Provider A's proprietary format
and the canonical NormalizedPaymentResponse / NormalizedRefundResponse.

Provider A specifics
--------------------
  - ID field:     "id"          → e.g. "pay_A_123"
  - Status field: "state"       → e.g. "created"
  - Amount:       "amount"      → INTEGER in minor units (10050 = 100.50)
  - Currency:     "currency"    → "SAR"
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from app.domain.enums import PaymentStatus, RefundStatus
from app.schemas import NormalizedPaymentResponse, NormalizedRefundResponse
from app.domain.enums import ProviderName
from app.domain.provider_port import PaymentProviderInterface
from app.services.provider_registry import register_provider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status mapping: provider-specific → canonical
# ---------------------------------------------------------------------------

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

    # -- port implementation -----------------------------------------------

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
    ) -> NormalizedPaymentResponse:
        """
        Call Provider A's payment creation endpoint and normalize the
        response.

        In a real deployment this would make an HTTP call; here we simulate
        the provider response for demonstration purposes.
        """
        # Amount is sent as integer (minor units) to Provider A
        amount_minor = int(amount * 100)

        payload = {
            "amount": amount_minor,
            "currency": currency,
            "customer_id": customer_id,
        }

        logger.info("Provider A — creating payment: %s", payload)

        # ---- Simulated provider response ---------------------------------
        raw: dict = {
            "id": f"pay_A_{uuid.uuid4().hex[:8]}",
            "state": "created",
            "amount": amount_minor,
            "currency": currency,
        }
        # ------------------------------------------------------------------

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

        # ---- Simulated provider response ---------------------------------
        raw: dict = {
            "id": f"ref_A_{uuid.uuid4().hex[:8]}",
            "state": "created",
            "amount": amount_minor,
            "original_payment": provider_reference,
        }
        # ------------------------------------------------------------------

        return NormalizedRefundResponse(
            provider_reference=raw["id"],
            status=self._normalize_refund_status(raw["state"]),
            refunded_amount=Decimal(raw["amount"]) / 100,
            raw_response=raw,
        )
