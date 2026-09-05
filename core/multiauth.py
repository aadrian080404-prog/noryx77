from dataclasses import dataclass
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


_MAX_ID = 256
_MAX_STATEMENT = 64 * 1024


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > _MAX_ID:
        raise ValueError(f"invalid_{field}")
    return value


def _statement(value: bytes) -> bytes:
    if not isinstance(value, bytes) or len(value) > _MAX_STATEMENT:
        raise ValueError("invalid_action_statement")
    return bytes(value)


def _message(action_id: str, epoch: int, statement: bytes) -> bytes:
    return b"NORYX7-MULTIAUTH-v1\x00" + action_id.encode() + b"\x00" + str(epoch).encode() + b"\x00" + sha256(statement).digest()


@dataclass(frozen=True)
class AuthorizationProof:
    action_id: str
    approvers: tuple[str, ...]
    threshold: int
    epoch: int

    def __post_init__(self):
        _text(self.action_id, "action_id")
        if not isinstance(self.approvers, tuple) or not self.approvers or any(not isinstance(x, str) or not x.strip() for x in self.approvers):
            raise ValueError("invalid_approvers")
        if len(set(self.approvers)) != len(self.approvers):
            raise ValueError("duplicate_approver")
        if not isinstance(self.threshold, int) or isinstance(self.threshold, bool) or self.threshold < 1:
            raise ValueError("invalid_threshold")
        if not isinstance(self.epoch, int) or isinstance(self.epoch, bool) or self.epoch < 0:
            raise ValueError("invalid_epoch")


class ThresholdAuthorizer:
    def __init__(self, *, required_threshold: int):
        if not isinstance(required_threshold, int) or isinstance(required_threshold, bool) or required_threshold < 1:
            raise ValueError("invalid_required_threshold")
        self.required_threshold = required_threshold

    def verify(self, proof: AuthorizationProof, *, action_id: str, epoch: int) -> bool:
        try:
            return (isinstance(proof, AuthorizationProof) and proof.action_id == action_id and proof.epoch == epoch
                    and proof.threshold >= self.required_threshold and len(proof.approvers) >= proof.threshold)
        except Exception:
            return False


@dataclass(frozen=True)
class SignedApproval:
    approver_id: str
    public_key: bytes
    signature: bytes

    def __post_init__(self):
        _text(self.approver_id, "approver_id")
        if not isinstance(self.public_key, bytes) or len(self.public_key) != 32:
            raise ValueError("invalid_public_key")
        if not isinstance(self.signature, bytes) or len(self.signature) != 64:
            raise ValueError("invalid_signature")


@dataclass(frozen=True)
class SignedAuthorizationProof:
    action_id: str
    epoch: int
    action_statement: bytes
    approvals: tuple[SignedApproval, ...]
    threshold: int

    def __post_init__(self):
        _text(self.action_id, "action_id")
        if not isinstance(self.epoch, int) or isinstance(self.epoch, bool) or self.epoch < 0:
            raise ValueError("invalid_epoch")
        _statement(self.action_statement)
        if not isinstance(self.approvals, tuple) or not self.approvals:
            raise ValueError("invalid_approvals")
        ids = [a.approver_id for a in self.approvals]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate_approver")
        if not isinstance(self.threshold, int) or isinstance(self.threshold, bool) or self.threshold < 1:
            raise ValueError("invalid_threshold")


class SignedApprovalAuthority:
    def __init__(self, *, required_threshold: int, trusted_keys: dict[str, bytes]):
        if not isinstance(required_threshold, int) or isinstance(required_threshold, bool) or required_threshold < 1:
            raise ValueError("invalid_required_threshold")
        if not isinstance(trusted_keys, dict) or not trusted_keys:
            raise ValueError("invalid_trusted_keys")
        self.required_threshold = required_threshold
        self._trusted = {}
        for party, key in trusted_keys.items():
            _text(party, "approver_id")
            if not isinstance(key, bytes) or len(key) != 32:
                raise ValueError("invalid_trusted_key")
            self._trusted[party] = bytes(key)
        self._revoked: set[str] = set()

    def revoke(self, approver_id: str) -> None:
        _text(approver_id, "approver_id")
        self._revoked.add(approver_id)

    def verify(self, proof: SignedAuthorizationProof, *, action_id: str, epoch: int, action_statement: bytes = b"") -> bool:
        try:
            if not isinstance(proof, SignedAuthorizationProof) or proof.action_id != action_id or proof.epoch != epoch or proof.action_statement != action_statement:
                return False
            if proof.threshold < self.required_threshold or len(proof.approvals) < proof.threshold:
                return False
            valid = 0
            seen = set()
            message = _message(proof.action_id, proof.epoch, proof.action_statement)
            for approval in proof.approvals:
                if approval.approver_id in seen or approval.approver_id in self._revoked:
                    return False
                seen.add(approval.approver_id)
                trusted = self._trusted.get(approval.approver_id)
                if trusted is None or trusted != approval.public_key:
                    return False
                Ed25519PublicKey.from_public_bytes(trusted).verify(approval.signature, message)
                valid += 1
            return valid >= self.required_threshold and valid >= proof.threshold
        except Exception:
            return False


def sign_approval(approver_id: str, private_key: Ed25519PrivateKey, *, action_id: str, epoch: int, action_statement: bytes = b"") -> SignedApproval:
    _text(approver_id, "approver_id")
    _text(action_id, "action_id")
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("invalid_private_key")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ValueError("invalid_epoch")
    _statement(action_statement)
    public = private_key.public_key().public_bytes_raw()
    return SignedApproval(approver_id, public, private_key.sign(_message(action_id, epoch, action_statement)))
