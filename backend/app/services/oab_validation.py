"""OAB registration validation — Strategy pattern.

Validating an OAB number against the official registry is a non-trivial,
external concern that we want to defer. By coding the registration flow against
the :class:`OABValidator` interface we can ship today with a permissive stub and
later drop in a real implementation (HTTP scraper, official API, manual review
queue, ...) without touching the services that depend on it.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OABValidationResult:
    verified: bool
    detail: str = ""


class OABValidator(ABC):
    """Strategy interface for verifying an OAB registration."""

    @abstractmethod
    async def validate(self, uf: str, number: str) -> OABValidationResult: ...


class NoopOABValidator(OABValidator):
    """Default strategy: accepts the number without verifying it.

    Marks the registration as *unverified* so the rest of the system can treat
    these lawyers accordingly (e.g. show a "pending verification" badge) until a
    real validator confirms them. This is the "deixe a validação para depois"
    placeholder called for in the requirements.
    """

    async def validate(self, uf: str, number: str) -> OABValidationResult:
        logger.info("OAB validation skipped (noop) for OAB/%s %s", uf, number)
        return OABValidationResult(
            verified=False, detail="Validação da OAB pendente (não implementada)"
        )


# A real implementation would look like:
#
# class RegistryOABValidator(OABValidator):
#     def __init__(self, http_client): ...
#     async def validate(self, uf, number) -> OABValidationResult:
#         # call cna.oab.org.br / official API, parse the response, etc.


def get_oab_validator() -> OABValidator:
    """Factory returning the active validation strategy.

    Centralised here so swapping strategies (or wiring config-based selection)
    is a one-line change.
    """
    return NoopOABValidator()
