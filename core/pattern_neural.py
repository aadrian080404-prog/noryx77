"""Small deterministic neural network for pattern scoring.

This is an auxiliary model, not the authority for actions, identity, safety,
or final verification. It can be replaced by a larger learned model later.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp


@dataclass(frozen=True)
class NeuralPattern:
    label: str
    score: float


class PatternNeuralNetwork:
    """Bounded one-hidden-layer MLP with fixed weights for reproducible routing."""

    def __init__(self) -> None:
        self._weights = (
            (0.7, -0.2, 0.4, 0.5, -0.3, 0.6),
            (-0.1, 0.8, 0.5, -0.4, 0.7, 0.2),
            (0.4, 0.3, -0.6, 0.8, 0.1, -0.5),
        )
        self._labels = ("causal", "structural", "anomalous")

    @staticmethod
    def _sigmoid(value: float) -> float:
        return 1.0 / (1.0 + exp(-max(-40.0, min(40.0, value))))

    def predict(self, features: tuple[float, ...]) -> tuple[NeuralPattern, ...]:
        if not isinstance(features, tuple) or len(features) != 6:
            raise ValueError("expected_six_features")
        if any(not isinstance(value, (int, float)) for value in features):
            raise TypeError("features_must_be_numeric")
        outputs = []
        for label, weights in zip(self._labels, self._weights):
            score = self._sigmoid(sum(weight * float(value) for weight, value in zip(weights, features)))
            outputs.append(NeuralPattern(label, score))
        return tuple(outputs)

    def recognize_text(self, text: str) -> tuple[NeuralPattern, ...]:
        if not isinstance(text, str):
            raise TypeError("text_must_be_string")
        lower = text.lower()
        features = (
            float(any(token in lower for token in ("because", "cause", "why", "impact"))),
            float(any(token in lower for token in ("system", "architecture", "network", "dependency"))),
            float(any(token in lower for token in ("unexpected", "anomaly", "exception", "failure"))),
            min(len(lower) / 1000.0, 1.0),
            float(any(token in lower for token in ("compare", "versus", "alternative"))),
            float(any(token in lower for token in ("equation", "data", "probability", "navier", "stokes"))),
        )
        return self.predict(features)
