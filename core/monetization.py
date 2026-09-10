"""Provider-neutral monetization boundary for NORYX7.

The UI may show a clearly labelled sponsored offer while a response is being
prepared. Revenue is recognized only from a verified provider callback; a
mere click, close, refresh, or synthetic event never creates earnings.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Mapping


@dataclass(frozen=True)
class MonetizationOffer:
    offer_id: str
    placement: str
    destination: str
    label: str = "Sponsored"
    skippable: bool = True


@dataclass(frozen=True)
class RevenueEvent:
    event_id: str
    offer_id: str
    event_type: str
    provider_reference: str
    amount_minor: int
    currency: str
    verified: bool


class MonetizationEngine:
    """Create transparent offers and admit only provider-verified revenue."""

    ALLOWED_EVENTS = ("impression", "qualified_click", "conversion", "reward")

    def create_offer(self, *, placement: str = "response_loading", destination: str) -> MonetizationOffer:
        if not isinstance(placement, str) or not placement.strip():
            raise ValueError("invalid_placement")
        if not isinstance(destination, str) or not destination.startswith(("https://", "http://")):
            raise ValueError("invalid_destination")
        offer_id = sha256(f"{placement}|{destination}".encode()).hexdigest()[:24]
        return MonetizationOffer(offer_id, placement, destination)

    def admit_provider_event(self, offer: MonetizationOffer, *, event_type: str, provider_reference: str, amount_minor: int, currency: str, verified: bool) -> RevenueEvent | None:
        if not isinstance(offer, MonetizationOffer) or event_type not in self.ALLOWED_EVENTS:
            raise ValueError("invalid_monetization_event")
        if not isinstance(provider_reference, str) or not provider_reference.strip():
            raise ValueError("provider_reference_required")
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor < 0:
            raise ValueError("invalid_amount")
        if not isinstance(currency, str) or len(currency) != 3:
            raise ValueError("invalid_currency")
        if not verified:
            return None
        event_id = sha256(f"{offer.offer_id}|{event_type}|{provider_reference}|{amount_minor}|{currency}".encode()).hexdigest()
        return RevenueEvent(event_id, offer.offer_id, event_type, provider_reference, amount_minor, currency.upper(), True)

    @staticmethod
    def loading_placement_enabled(offer: MonetizationOffer) -> bool:
        return isinstance(offer, MonetizationOffer) and offer.placement == "response_loading"
