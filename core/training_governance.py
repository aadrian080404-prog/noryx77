"""Bounded training and model-improvement governance for NORYX7.

This layer does not silently retrain a foundation model at runtime. It records
eligible feedback, binds datasets to provenance, and requires deterministic
evaluation before a candidate model can be promoted.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any


MAX_DATASET_ITEMS = 100_000
MAX_TEXT_BYTES = 64 * 1024


class TrainingStage(str, Enum):
    COLLECTED = "collected"
    CURATED = "curated"
    EVALUATED = "evaluated"
    PROMOTED = "promoted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class TrainingExample:
    example_id: str
    input_text: str
    target_text: str
    source: str
    consent: bool = False

    def __post_init__(self):
        if not isinstance(self.example_id, str) or not self.example_id.strip():
            raise ValueError("training_example_id_required")
        for value, name in ((self.input_text, "training_input_required"), (self.target_text, "training_target_required")):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(name)
            if len(value.encode("utf-8")) > MAX_TEXT_BYTES:
                raise ValueError("training_text_too_large")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("training_source_required")
        if not isinstance(self.consent, bool):
            raise ValueError("training_consent_required")


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    examples: tuple[TrainingExample, ...]
    digest: str

    def __post_init__(self):
        if not isinstance(self.dataset_id, str) or not self.dataset_id.strip():
            raise ValueError("dataset_id_required")
        if not isinstance(self.examples, tuple) or not self.examples or len(self.examples) > MAX_DATASET_ITEMS:
            raise ValueError("invalid_training_dataset")
        if any(not isinstance(item, TrainingExample) for item in self.examples):
            raise TypeError("training_example_required")
        if not isinstance(self.digest, str) or len(self.digest) != 64:
            raise ValueError("invalid_dataset_digest")


@dataclass(frozen=True)
class EvaluationReport:
    candidate_id: str
    baseline_score: float
    candidate_score: float
    safety_score: float
    regression_free: bool

    def __post_init__(self):
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id_required")
        for score in (self.baseline_score, self.candidate_score, self.safety_score):
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0.0 <= float(score) <= 1.0:
                raise ValueError("invalid_evaluation_score")
        if not isinstance(self.regression_free, bool):
            raise ValueError("invalid_regression_flag")


class TrainingGovernance:
    """Consent-bound dataset curation and deterministic promotion gate."""

    @staticmethod
    def _digest(examples: tuple[TrainingExample, ...]) -> str:
        payload = [
            {
                "example_id": item.example_id,
                "input_text": item.input_text,
                "target_text": item.target_text,
                "source": item.source,
            }
            for item in examples
        ]
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()

    def curate(self, dataset_id: str, examples: tuple[TrainingExample, ...]) -> DatasetManifest:
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("dataset_id_required")
        if not isinstance(examples, tuple):
            raise TypeError("training_examples_tuple_required")
        if any(not item.consent for item in examples):
            raise PermissionError("training_consent_required")
        return DatasetManifest(dataset_id=dataset_id, examples=examples, digest=self._digest(examples))

    @staticmethod
    def admit(report: EvaluationReport, *, minimum_gain: float = 0.01, minimum_safety: float = 0.99) -> TrainingStage:
        if isinstance(minimum_gain, bool) or not isinstance(minimum_gain, (int, float)) or not 0.0 <= minimum_gain <= 1.0:
            raise ValueError("invalid_minimum_gain")
        if isinstance(minimum_safety, bool) or not isinstance(minimum_safety, (int, float)) or not 0.0 <= minimum_safety <= 1.0:
            raise ValueError("invalid_minimum_safety")
        gain = report.candidate_score - report.baseline_score
        if report.regression_free and gain >= minimum_gain and report.safety_score >= minimum_safety:
            return TrainingStage.PROMOTED
        return TrainingStage.REJECTED
