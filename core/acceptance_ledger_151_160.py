"""Authenticated append-only ledger for HYPERSYNTH export admissions."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
from typing import Iterable

from .crypto import CryptoEnvelope, CryptoIntegrity
from .export_acceptance_141_150 import AcceptanceReceipt, ExportAcceptanceController


@dataclass(frozen=True)
class AcceptanceLedgerRecord:
    sequence: int
    manifest_tag: str
    receipt_tag: str
    session_id: str
    task_id: str
    risk_class: str
    previous_tag: str
    tag: str


class AcceptanceLedger:
    """Fail-closed authenticated chain over cryptographically valid receipts."""

    DOMAIN = "hypersynth_acceptance_ledger"
    TAG_LENGTH = 64

    def __init__(self, crypto: CryptoIntegrity):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto")
        self.crypto = crypto
        self._records: list[AcceptanceLedgerRecord] = []
        self._sealed = False
        self._seal_length: int | None = None
        self._seal_root: str | None = None

    @property
    def records(self) -> tuple[AcceptanceLedgerRecord, ...]:
        return tuple(self._records)

    @property
    def sealed(self) -> bool:
        return self._sealed

    @property
    def seal_root(self) -> str | None:
        return self._seal_root

    def _verify_receipt_crypto(self, receipt: AcceptanceReceipt) -> bool:
        if not isinstance(receipt, AcceptanceReceipt):
            return False
        if receipt.algorithm != ExportAcceptanceController.ALGORITHM or receipt.version != ExportAcceptanceController.VERSION:
            return False
        if receipt.counter != ExportAcceptanceController.COUNTER:
            return False
        if receipt.nonce != receipt.manifest_tag:
            return False
        payload = ExportAcceptanceController._receipt_payload(
            nonce=receipt.nonce, manifest_tag=receipt.manifest_tag,
            session_id=receipt.session_id, task_id=receipt.task_id,
            risk_class=receipt.risk_class,
        )
        envelope = CryptoEnvelope(
            ExportAcceptanceController.DOMAIN, receipt.nonce, receipt.counter,
            self.crypto.canonical(payload), receipt.receipt_tag,
            receipt.algorithm, receipt.version,
        )
        return self.crypto.verify(envelope, consume=False)

    def append(self, receipt: AcceptanceReceipt) -> AcceptanceLedgerRecord:
        if self._sealed:
            raise RuntimeError("ledger_sealed")
        if not self._verify_receipt_crypto(receipt):
            raise ValueError("invalid_authenticated_receipt")
        if any(item.manifest_tag == receipt.manifest_tag for item in self._records):
            raise ValueError("duplicate_manifest_admission")
        sequence = len(self._records) + 1
        previous = self._records[-1].tag if self._records else ""
        material = {
            "sequence": sequence,
            "manifest_tag": receipt.manifest_tag,
            "receipt_tag": receipt.receipt_tag,
            "session_id": receipt.session_id,
            "task_id": receipt.task_id,
            "risk_class": receipt.risk_class,
            "previous_tag": previous,
        }
        tag = self.crypto.digest(self.DOMAIN, material)
        record = AcceptanceLedgerRecord(
            sequence, receipt.manifest_tag, receipt.receipt_tag,
            receipt.session_id, receipt.task_id, receipt.risk_class,
            previous, tag,
        )
        self._records.append(record)
        return record

    def _root(self, records: Iterable[AcceptanceLedgerRecord]) -> str:
        records = tuple(records)
        return self.crypto.digest(
            self.DOMAIN + ":root",
            {"length": len(records), "tail": records[-1].tag if records else ""},
        )

    def seal(self) -> tuple[AcceptanceLedgerRecord, ...]:
        if self._sealed:
            raise RuntimeError("ledger_already_sealed")
        if not self.verify(self._records):
            raise RuntimeError("ledger_integrity_failure")
        self._seal_length = len(self._records)
        self._seal_root = self._root(self._records)
        self._sealed = True
        return self.records

    def verify(self, records: Iterable[AcceptanceLedgerRecord] | None = None) -> bool:
        try:
            records = tuple(self._records if records is None else records)
            if len(records) != len(self._records):
                return False
            previous = ""
            seen: set[str] = set()
            manifests: set[str] = set()
            for sequence, record in enumerate(records, 1):
                if not isinstance(record, AcceptanceLedgerRecord):
                    return False
                if record.sequence != sequence or record.previous_tag != previous:
                    return False
                if not all(isinstance(x, str) and x.strip() for x in (
                    record.manifest_tag, record.receipt_tag, record.session_id,
                    record.task_id, record.risk_class, record.tag
                )):
                    return False
                if len(record.manifest_tag) != self.TAG_LENGTH or len(record.receipt_tag) != self.TAG_LENGTH or len(record.tag) != self.TAG_LENGTH:
                    return False
                if record.tag in seen or record.manifest_tag in manifests:
                    return False
                material = {
                    "sequence": sequence,
                    "manifest_tag": record.manifest_tag,
                    "receipt_tag": record.receipt_tag,
                    "session_id": record.session_id,
                    "task_id": record.task_id,
                    "risk_class": record.risk_class,
                    "previous_tag": previous,
                }
                expected = self.crypto.digest(self.DOMAIN, material)
                if not hmac.compare_digest(expected, record.tag):
                    return False
                seen.add(record.tag); manifests.add(record.manifest_tag); previous = record.tag

            # Seal metadata is itself part of the integrity state. Never allow
            # flipping the mutable _sealed flag to bypass an existing seal.
            has_length = self._seal_length is not None
            has_root = self._seal_root is not None
            if has_length != has_root:
                return False
            if self._sealed and not (has_length and has_root):
                return False
            if has_length and has_root:
                if len(records) != self._seal_length:
                    return False
                if not hmac.compare_digest(self._root(records), self._seal_root):
                    return False
            return True
        except Exception:
            return False


__all__ = ["AcceptanceLedgerRecord", "AcceptanceLedger"]
