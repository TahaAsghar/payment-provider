"""
Provider registry — holds the decorator and the global registry dict.

This module is deliberately kept separate from provider_factory.py to
avoid circular imports: adapters import the decorator from here, and
the factory imports the registry dict from here + triggers adapter discovery.
"""

from __future__ import annotations

import logging
from typing import Callable

from app.domain.enums import ProviderName
from app.domain.provider_port import PaymentProviderInterface

logger = logging.getLogger(__name__)


_PROVIDER_REGISTRY: dict[ProviderName, type[PaymentProviderInterface]] = {}


def register_provider(
    name: ProviderName,
) -> Callable[[type[PaymentProviderInterface]], type[PaymentProviderInterface]]:
    """
    Class decorator that registers a provider adapter in the global registry.

    Usage::

        @register_provider(ProviderName.PROVIDER_A)
        class ProviderAClient(PaymentProviderInterface):
            ...
    """

    def decorator(
        cls: type[PaymentProviderInterface],
    ) -> type[PaymentProviderInterface]:
        if name in _PROVIDER_REGISTRY:
            raise RuntimeError(
                f"Duplicate provider registration for '{name.value}': "
                f"{_PROVIDER_REGISTRY[name].__name__} and {cls.__name__}"
            )
        _PROVIDER_REGISTRY[name] = cls
        logger.info("Registered provider adapter: %s → %s", name.value, cls.__name__)
        return cls

    return decorator


def get_registry() -> dict[ProviderName, type[PaymentProviderInterface]]:
    """Return a read-only view of the current registry (for the factory)."""
    return _PROVIDER_REGISTRY
