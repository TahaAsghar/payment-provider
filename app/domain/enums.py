"""
Canonical status enums used throughout the domain layer.

These enums standardize the heterogeneous status values returned by
different external payment providers into a single vocabulary that the
rest of the application can depend on.
"""

from enum import Enum


class PaymentStatus(str, Enum):
    """Normalized payment lifecycle status."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    CANCELLED = "CANCELLED"


class RefundStatus(str, Enum):
    """Normalized refund lifecycle status."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ProviderName(str, Enum):
    """Supported payment provider identifiers."""

    PROVIDER_A = "provider_a"
    PROVIDER_B = "provider_b"
