"""Authoritative routing policy shared by resource routing and supervision."""

from types import MappingProxyType


MODEL_ORDER = ("micro", "small", "medium", "large", "frontier")
TASK_MODEL_HINTS = MappingProxyType(
    {
        "simple": "micro",
        "classification": "small",
        "analysis": "medium",
        "research": "large",
        "reasoning": "large",
        "planning": "large",
        "frontier": "frontier",
    }
)
