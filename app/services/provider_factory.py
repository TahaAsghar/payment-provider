from __future__ import annotations

import importlib
import logging
import os

from app.domain.enums import ProviderName
from app.domain.provider_port import PaymentProviderInterface
from app.services.provider_registry import get_registry

logger = logging.getLogger(__name__)


def _ensure_adapter_loaded(name: ProviderName) -> None:
    """
    Lazily import the adapter module for ``name`` if it hasn't been
    imported yet.

    Convention: ``ProviderName.PROVIDER_A`` ("provider_a")
                → ``app.adapters.provider_a_client``

    The import triggers the ``@register_provider`` decorator inside
    that module, which populates the registry.
    """
    registry = get_registry()
    if name in registry:
        return  # already loaded

    if name == ProviderName.PROVIDER_A:
        module_name = "app.adapters.providerA_adapter"
    else:
        module_name = f"app.adapters.{name.value}_adapter"
        
    try:
        importlib.import_module(module_name)
        logger.info("Lazy-loaded adapter module: %s", module_name)
    except ModuleNotFoundError:
        raise ValueError(
            f"No adapter module found for provider '{name.value}'. "
            f"Expected module: {module_name}"
        )
    except Exception:
        logger.exception("Failed to import adapter module: %s", module_name)
        raise


def get_provider(name: ProviderName) -> PaymentProviderInterface:
    """
    Return a configured PaymentProviderInterface for the given provider.

    The adapter module is imported on first call; subsequent calls use
    the cached registry entry.

    Raises ValueError if the provider has no matching adapter module.
    """
    _ensure_adapter_loaded(name)

    registry = get_registry()
    cls = registry.get(name)
    if cls is None:
        raise ValueError(
            f"Adapter module for '{name.value}' was imported but did not "
            f"register itself via @register_provider. Check the decorator."
        )

    return cls()
