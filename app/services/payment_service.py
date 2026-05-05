"""
PaymentService — core use-case orchestration.

This service coordinates between domain ports (provider gateway,
repository) without ever depending on a specific framework or adapter.
It is the single source of truth for payment lifecycle operations.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from app.domain.enums import PaymentStatus, RefundStatus
from app.schemas import (
    CreatePaymentRequest,
    CreateRefundRequest,
    NormalizedPaymentResponse,
    PaymentDetail,
    RefundDetail,
)
from app.domain.provider_port import PaymentProviderInterface
from app.domain.repository_port import PaymentRepositoryInterface
from app.services.provider_factory import get_provider
from app.domain.exceptions import (
    PaymentNotFoundError,
    PaymentNotRefundableError,
    RefundAmountExceededError,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Application service that drives the create-payment, get-payment,
    and refund use-cases.
    """

    def __init__(self, repository: PaymentRepositoryInterface) -> None:
        self._repo = repository


    async def create_payment(self, request: CreatePaymentRequest) -> PaymentDetail:
        """
        1. Persist a PENDING payment row.
        2. Call the external provider.
        3. Update the row with the provider's reference & status.
        """
        # 1. Persist initial record
        payment = await self._repo.create_payment(
            provider=request.provider,
            amount=request.amount,
            currency=request.currency,
            customer_id=request.customer_id,
            status=PaymentStatus.PENDING,
        )
        logger.info("Created PENDING payment %s", payment.id)

        # 2. Call provider
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

        # 3. Update record with provider response
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
        """
        1. Validate that the payment exists and is refundable.
        2. Call the provider's refund endpoint.
        3. Persist the refund record and update the payment status.
        """
        payment = await self._repo.get_payment(payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id)

        if payment.status not in (
            PaymentStatus.SUCCESS,
            PaymentStatus.PENDING,
            PaymentStatus.PARTIALLY_REFUNDED,
        ):
            raise PaymentNotRefundableError(payment_id, payment.status)

        if request.amount > payment.amount:
            raise RefundAmountExceededError(
                payment_id, request.amount, payment.amount
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
            if request.amount == payment.amount
            else PaymentStatus.PARTIALLY_REFUNDED
        )
        await self._repo.update_payment_status(payment_id, status=new_status)

        logger.info("Refund %s created for payment %s", refund.id, payment_id)
        return refund


