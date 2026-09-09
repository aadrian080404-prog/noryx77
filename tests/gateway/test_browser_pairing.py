import pytest

from gateway.auth import SessionAuthority, SessionError


def test_browser_pairing_issues_verifiable_session_without_bootstrap():
    authority = SessionAuthority(
        bootstrap_token="bootstrap-secret",
        signing_secret="s" * 32,
        browser_pairing_code="pairing-secret",
    )

    token = authority.issue_browser_pairing("pairing-secret", "noryx-browser-android")

    payload = authority.verify(token)
    assert payload["client_id"] == "noryx-browser-android"


def test_browser_pairing_rejects_wrong_code():
    authority = SessionAuthority(
        bootstrap_token="bootstrap-secret",
        signing_secret="s" * 32,
        browser_pairing_code="pairing-secret",
    )

    with pytest.raises(SessionError, match="browser_pairing_failed"):
        authority.issue_browser_pairing("wrong", "noryx-browser-android")


def test_browser_pairing_is_disabled_without_server_secret():
    authority = SessionAuthority(
        bootstrap_token="bootstrap-secret",
        signing_secret="s" * 32,
    )

    with pytest.raises(SessionError, match="browser_pairing_disabled"):
        authority.issue_browser_pairing("anything", "noryx-browser-android")
