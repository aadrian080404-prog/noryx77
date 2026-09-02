"""Authenticated append-only ledger for HYPERSYNTH export admissions."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
from typing import Iterable

from .crypto import CryptoIntegrity
from .export_acceptance_141_150 import AcceptanceReceipt


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
    """Fail-closed authenticated chain over accepted export receipts."""

    DOMAIN = "hypersynth_acceptance_ledger"
    TAG_LENGTH = 64

    def __init__(self, crypto: CryptoIntegrity):
        if not isinstance(crypto, CryptoIntegrity):
            raise TypeError("invalid_crypto")
        self.crypto = crypto
        self._records: list[AcceptanceLedgerRecord] = []
        self._sealed = False

    @property
    def records(self) -> tuple[AcceptanceLedgerRecord, ...]:
        return tuple(self._records)

    def append(self, receipt: AcceptanceReceipt) -> AcceptanceLedgerRecord:
        if self._sealed:
            raise RuntimeError("ledger_sealed")
        if not isinstance(receipt, AcceptanceReceipt):
            raise TypeError("invalid_acceptance_receipt")
        if not all(isinstance(x, str) and x.strip() for x in (
            receipt.manifest_tag, receipt.receipt_tag, receipt.session_id,
            receipt.task_id, receipt.risk_class
        )):
            raise ValueError("invalid_acceptance_receipt_identity")
        if len(receipt.manifest_tag) != self.TAG_LENGTH or len(receipt.receipt_tag) != self.TAG_LENGTH:
            raise ValueError("invalid_acceptance_receipt_tag")
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

    def seal(self) -> tuple[AcceptanceLedgerRecord, ...]:
        if self._sealed:
            raise RuntimeError("ledger_already_sealed")
        if not self.verify(self._records):
            raise RuntimeError("ledger_integrity_failure")
        self._sealed = True
        return self.records

    def verify(self, records: Iterable[AcceptanceLedgerRecord] | None = None) -> bool:
        try:
            records = tuple(self._records if records is None else records)
            previous = ""
            seen: set[str] = set()
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
                if record.tag in seen:
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
                seen.add(record.tag)
                previous = record.tag
            return True
        except Exception:
            return False


__all__ = ["AcceptanceLedgerRecord", "AcceptanceLedger"]
