from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from app.helpers.enums import PaymentStatus, RefundStatus
from app.schemas import (
    CreatePaymentRequest,
    CreateRefundRequest,
    NormalizedPaymentResponse,
    PaymentDetail,
    RefundDetail,
)
from app.interface.provider_interface import PaymentProviderInterface
from app.interface.repository_interface import PaymentRepositoryInterface
from app.services.provider_factory import get_provider
from app.helpers.exceptions import (
    PaymentNotFoundError,
    PaymentNotRefundableError,
    RefundAmountExceededError,
)

logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(self, repository: PaymentRepositoryInterface) -> None:
        self._repo = repository


    async def create_payment(self, request: CreatePaymentRequest) -> PaymentDetail:

        payment = await self._repo.create_payment(
            provider=request.provider,
            amount=request.amount,
            currency=request.currency,
            customer_id=request.customer_id,
            status=PaymentStatus.PENDING,
        )
        logger.info("Created PENDING payment %s", payment.id)

        provider: PaymentProviderInterface = get_provider(request.provider)
        try:
            result: NormalizedPaymentResponse = await provider.create_payment(
                amount=request.amount,
                currency=request.currency,
                customer_id=request.customer_id,
            )
        except Exception:
            logger.exception(
                "Provider %s failed for payment %s", request.provider, payment.id
            )
            await self._repo.update_payment_status(
                payment.id, status=PaymentStatus.FAILED
            )
            raise

        payment = await self._repo.update_payment_status(
            payment.id,
            status=result.status,
            provider_reference=result.provider_reference,
            raw_response=result.raw_response,
        )
        logger.info(
            "Payment %s updated → status=%s, ref=%s",
            payment.id,
            payment.status,
            payment.provider_reference,
        )
        return payment


    async def get_payment(self, payment_id: uuid.UUID) -> PaymentDetail:
        payment = await self._repo.get_payment(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)
        return payment

    async def refund_payment(
        self,
        payment_id: uuid.UUID,
        request: CreateRefundRequest,
    ) -> RefundDetail:

        payment = await self._repo.get_payment_for_update(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)

        if payment.status not in (
            PaymentStatus.SUCCESS,
            PaymentStatus.PENDING,
            PaymentStatus.PARTIALLY_REFUNDED,
        ):
            raise PaymentNotRefundableError(payment_id, payment.status)

        existing_refunds = await self._repo.get_refunds_for_payment(payment_id)
        total_refunded = sum(r.amount for r in existing_refunds)
        available = payment.amount - total_refunded

        if request.amount > available:
            raise RefundAmountExceededError(
                payment_id, request.amount, available
            )

        provider = get_provider(payment.provider)
        refund_result = await provider.refund_payment(
            provider_reference=payment.provider_reference or "",
            amount=request.amount,
            reason=request.reason,
        )

        refund = await self._repo.create_refund(
            payment_id=payment_id,
            amount=request.amount,
            reason=request.reason,
            status=refund_result.status,
            provider_reference=refund_result.provider_reference,
            raw_response=refund_result.raw_response,
        )

        new_status = (
            PaymentStatus.REFUNDED
            if (total_refunded + request.amount) >= payment.amount
            else PaymentStatus.PARTIALLY_REFUNDED
        )
        await self._repo.update_payment_status(payment_id, status=new_status)

        logger.info("Refund %s created for payment %s", refund.id, payment_id)
        return refund


