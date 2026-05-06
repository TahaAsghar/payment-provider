from enum import Enum


class PaymentStatus(str, Enum):

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    CANCELLED = "CANCELLED"


class RefundStatus(str, Enum):

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ProviderName(str, Enum):

    PROVIDER_A = "provider_a"
    PROVIDER_B = "provider_b"
