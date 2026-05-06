from __future__ import annotations

import logging
from typing import Callable

from app.helpers.enums import ProviderName
from app.interface.provider_interface import PaymentProviderInterface

logger = logging.getLogger(__name__)


_PROVIDER_REGISTRY: dict[ProviderName, type[PaymentProviderInterface]] = {}


def register_provider(
    name: ProviderName,
) -> Callable[[type[PaymentProviderInterface]], type[PaymentProviderInterface]]:
    """
    Class decorator that registers a provider adapter in the global registry.
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
    return _PROVIDER_REGISTRY
