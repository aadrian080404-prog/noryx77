from __future__ import annotations


class ResourceSelector:
    """Deterministic, temporary routing heuristic for task-to-resource selection.

    This selector intentionally does not execute any task and does not know about
    orchestration logic. It only estimates task complexity and maps it to a
    resource identifier.
    """

    _VALID_RESOURCES = {"small", "large"}

    def estimate_complexity(self, task: str) -> str:
        """Temporary heuristic: simple tasks map to 'small'; more involved tasks map to 'large'."""
        normalized = (task or "").strip().lower()

        if not normalized:
            return "small"

        complexity_keywords = {
            "plan",
            "planning",
            "organize",
            "organization",
            "itinerary",
            "budget",
            "travel",
            "schedule",
            "compare",
            "document",
            "documents",
            "strategy",
            "research",
            "analysis",
            "complex",
            "comprehensive",
            "hotel",
            "trasporto",
            "documenti",
            "pianifica",
        }

        tokens = set(normalized.replace("-", " ").split())
        if tokens & complexity_keywords:
            return "large"

        if len(normalized.split()) >= 8:
            return "large"

        return "small"

    def select(self, task: str) -> str:
        """Return a deterministic resource id for the given task."""
        resource = self.estimate_complexity(task)
        if resource not in self._VALID_RESOURCES:
            raise ValueError(f"Unsupported resource '{resource}'")
        return resource
