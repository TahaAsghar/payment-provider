import uuid
from decimal import Decimal

from app.domain.enums import PaymentStatus


class PaymentNotFoundError(Exception):
    def __init__(self, payment_id: uuid.UUID) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id} not found")


class PaymentNotRefundableError(Exception):
    def __init__(self, payment_id: uuid.UUID, status: PaymentStatus) -> None:
        self.payment_id = payment_id
        self.status = status
        super().__init__(
            f"Payment {payment_id} is not refundable (current status: {status})"
        )


class RefundAmountExceededError(Exception):
    def __init__(
        self, payment_id: uuid.UUID, requested: Decimal, available: Decimal
    ) -> None:
        self.payment_id = payment_id
        super().__init__(
            f"Refund amount {requested} exceeds payment amount {available} "
            f"for payment {payment_id}"
        )
