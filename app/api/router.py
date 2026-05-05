from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.dependencies import (
    IdempotencyResult,
    get_payment_service,
    idempotency_guard,
)
from app.schemas import (
    CreatePaymentRequest,
    CreateRefundRequest,
    PaymentDetail,
    RefundDetail,
)
from app.services.payment_service import PaymentService
from app.domain.exceptions import (
    PaymentNotFoundError,
    PaymentNotRefundableError,
    RefundAmountExceededError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])



@router.post(
    "",
    response_model=PaymentDetail,
    status_code=201,
    summary="Create a new payment",
    description="Initiate a payment through the specified provider.",
)
async def create_payment(
    body: CreatePaymentRequest,
    service: PaymentService = Depends(get_payment_service),
    idem: IdempotencyResult = Depends(idempotency_guard),
) -> JSONResponse | PaymentDetail:
    # Short-circuit on idempotent duplicate
    if idem.is_cached:
        return JSONResponse(
            content=idem.cached_response,
            status_code=idem.cached_status_code,
        )

    try:
        payment = await service.create_payment(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error creating payment")
        raise HTTPException(status_code=502, detail="Payment provider error")

    response_body = payment.model_dump(mode="json")

    # Mark idempotency entry as completed
    await idem.mark_completed(201, response_body)

    return JSONResponse(content=response_body, status_code=201)


@router.get(
    "/{payment_id}",
    response_model=PaymentDetail,
    summary="Retrieve a payment by ID",
)
async def get_payment(
    payment_id: uuid.UUID,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentDetail:
    try:
        return await service.get_payment(payment_id)
    except PaymentNotFoundError:
        raise HTTPException(status_code=404, detail="Payment not found")


@router.post(
    "/{payment_id}/refund",
    response_model=RefundDetail,
    status_code=201,
    summary="Refund a payment",
    description="Initiate a full or partial refund for an existing payment.",
)
async def refund_payment(
    payment_id: uuid.UUID,
    body: CreateRefundRequest,
    service: PaymentService = Depends(get_payment_service),
    idem: IdempotencyResult = Depends(idempotency_guard),
) -> JSONResponse | RefundDetail:
    # Short-circuit on idempotent duplicate
    if idem.is_cached:
        return JSONResponse(
            content=idem.cached_response,
            status_code=idem.cached_status_code,
        )

    try:
        refund = await service.refund_payment(payment_id, body)
    except PaymentNotFoundError:
        raise HTTPException(status_code=404, detail="Payment not found")
    except PaymentNotRefundableError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RefundAmountExceededError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Unexpected error processing refund")
        raise HTTPException(status_code=502, detail="Refund provider error")

    response_body = refund.model_dump(mode="json")
    await idem.mark_completed(201, response_body)

    return JSONResponse(content=response_body, status_code=201)
