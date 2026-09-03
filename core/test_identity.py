import unittest

from dataclasses import replace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .identity import AgentIdentity, AgentIdentityAuthority


class AgentIdentityTests(unittest.TestCase):
    def test_generate_and_verify_identity(self):
        identity, private_key = AgentIdentityAuthority.generate("agent-a")
        self.assertTrue(AgentIdentityAuthority.verify_identity(identity))
        self.assertIsInstance(private_key, Ed25519PrivateKey)

    def test_signed_attestation_verifies(self):
        identity, private_key = AgentIdentityAuthority.generate("agent-a")
        attestation = AgentIdentityAuthority.sign(identity, private_key, b"boot-state:v1")
        self.assertTrue(AgentIdentityAuthority.verify(attestation))

    def test_statement_tampering_is_rejected(self):
        identity, private_key = AgentIdentityAuthority.generate("agent-a")
        attestation = AgentIdentityAuthority.sign(identity, private_key, b"boot-state:v1")
        forged = replace(attestation, statement=b"boot-state:forged")
        self.assertFalse(AgentIdentityAuthority.verify(forged))

    def test_signature_tampering_is_rejected(self):
        identity, private_key = AgentIdentityAuthority.generate("agent-a")
        attestation = AgentIdentityAuthority.sign(identity, private_key, b"boot-state:v1")
        forged = replace(attestation, signature=b"x" * len(attestation.signature))
        self.assertFalse(AgentIdentityAuthority.verify(forged))

    def test_identity_id_substitution_is_rejected(self):
        identity, private_key = AgentIdentityAuthority.generate("agent-a")
        attestation = AgentIdentityAuthority.sign(identity, private_key, b"boot-state:v1")
        forged_identity = replace(identity, agent_id="agent-b")
        forged = replace(attestation, identity=forged_identity)
        self.assertFalse(AgentIdentityAuthority.verify(forged))

    def test_public_key_substitution_is_rejected(self):
        identity, private_key = AgentIdentityAuthority.generate("agent-a")
        attestation = AgentIdentityAuthority.sign(identity, private_key, b"boot-state:v1")
        other_identity, _ = AgentIdentityAuthority.generate("agent-b")
        forged_identity = replace(identity, public_key=other_identity.public_key)
        forged = replace(attestation, identity=forged_identity)
        self.assertFalse(AgentIdentityAuthority.verify(forged))

    def test_private_key_identity_mismatch_is_rejected(self):
        identity, _ = AgentIdentityAuthority.generate("agent-a")
        _, wrong_private = AgentIdentityAuthority.generate("agent-b")
        with self.assertRaisesRegex(ValueError, "identity_private_key_mismatch"):
            AgentIdentityAuthority.sign(identity, wrong_private, b"boot-state:v1")

    def test_malformed_identity_is_rejected(self):
        identity, _ = AgentIdentityAuthority.generate("agent-a")
        forged = replace(identity, public_key=b"x")
        self.assertFalse(AgentIdentityAuthority.verify_identity(forged))

    def test_malformed_attestation_is_rejected(self):
        identity, private_key = AgentIdentityAuthority.generate("agent-a")
        attestation = AgentIdentityAuthority.sign(identity, private_key, b"boot-state:v1")
        forged = replace(attestation, signature=b"x")
        self.assertFalse(AgentIdentityAuthority.verify(forged))

    def test_wrong_identity_version_is_rejected(self):
        identity, private_key = AgentIdentityAuthority.generate("agent-a")
        attestation = AgentIdentityAuthority.sign(identity, private_key, b"boot-state:v1")
        forged_identity = replace(identity, version=2)
        forged = replace(attestation, identity=forged_identity)
        self.assertFalse(AgentIdentityAuthority.verify(forged))


if __name__ == "__main__":
    unittest.main()
