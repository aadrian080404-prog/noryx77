import pytest

from .crypto import CryptoEnvelope, CryptoIntegrity


class SpoofedCryptoEnvelope(CryptoEnvelope):
    def __getattribute__(self, name):
        if name == "algorithm":
            return "HMAC-SHA256"
        if name == "version":
            return 1
        if name == "domain":
            return "memory"
        if name == "nonce":
            return "spoofed-nonce"
        if name == "counter":
            return 0
        if name == "payload":
            return b'{"spoofed":true}'
        if name == "tag":
            return "0" * 64
        return super().__getattribute__(name)


@pytest.fixture
def crypto():
    return CryptoIntegrity(b"k" * 32)


def test_attack_245_crypto_envelope_subclass_is_rejected(crypto):
    canonical = crypto.sign("test", {"value": 1}, 0, nonce="nonce-245")
    spoofed = SpoofedCryptoEnvelope(
        canonical.domain,
        canonical.nonce,
        canonical.counter,
        canonical.payload,
        canonical.tag,
        canonical.algorithm,
        canonical.version,
    )

    assert crypto.verify(spoofed) is False


def test_attack_246_crypto_envelope_subclass_cannot_bypass_with_valid_tag(crypto):
    canonical = crypto.sign("test", {"value": 2}, 0, nonce="nonce-246")
    spoofed = SpoofedCryptoEnvelope(
        canonical.domain,
        canonical.nonce,
        canonical.counter,
        canonical.payload,
        canonical.tag,
        canonical.algorithm,
        canonical.version,
    )

    assert type(spoofed) is not CryptoEnvelope
    assert crypto.verify(spoofed, consume=False) is False


def test_attack_247_canonical_crypto_envelope_remains_accepted(crypto):
    envelope = crypto.sign("test", {"value": 3}, 0, nonce="nonce-247")

    assert type(envelope) is CryptoEnvelope
    assert crypto.verify(envelope) is True
    assert crypto.verify(envelope) is False
