from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.helpers.enums import PaymentStatus, ProviderName, RefundStatus


class CreatePaymentRequest(BaseModel):
    """Inbound payload for creating a new payment."""

    amount: Decimal = Field(..., gt=0, description="Payment amount (e.g. 100.50)")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 code")
    customer_id: str = Field(..., min_length=1, description="Opaque customer identifier")
    provider: ProviderName


class CreateRefundRequest(BaseModel):
    """Inbound payload for initiating a refund."""

    amount: Decimal = Field(..., gt=0, description="Refund amount")
    reason: str = Field(..., min_length=1, max_length=500)

class NormalizedPaymentResponse(BaseModel):
    """
    Canonical representation that every provider adapter MUST return.

    Adapters translate provider-specific JSON into this model so the rest
    of the system speaks a single language.
    """

    provider_reference: str = Field(..., description="ID assigned by the provider")
    status: PaymentStatus
    amount: Decimal
    currency: str
    raw_response: dict[str, Any] = Field(
        default_factory=dict,
        description="Verbatim provider response stored for audit / debugging",
    )


class NormalizedRefundResponse(BaseModel):
    """Canonical refund response returned by provider adapters."""

    provider_reference: str
    status: RefundStatus
    refunded_amount: Decimal
    raw_response: dict[str, Any] = Field(default_factory=dict)

class PaymentDetail(BaseModel):
    """Full payment record returned on GET /payments/{id}."""

    id: uuid.UUID
    provider: ProviderName
    provider_reference: Optional[str] = None
    amount: Decimal
    currency: str
    customer_id: str
    status: PaymentStatus
    raw_response: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RefundDetail(BaseModel):
    """Refund record attached to a payment."""

    id: uuid.UUID
    payment_id: uuid.UUID
    provider_reference: Optional[str] = None
    amount: Decimal
    reason: str
    status: RefundStatus
    raw_response: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}
