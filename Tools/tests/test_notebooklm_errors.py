from __future__ import annotations

from scripts.notebooklm_errors import (
    classify_notebooklm_error,
    should_abort_notebooklm_bootstrap,
)


def test_classify_notebooklm_error_detects_auth_expiry() -> None:
    assert classify_notebooklm_error("RPC Error 16: Authentication expired") == "auth"


def test_classify_notebooklm_error_detects_notebooklm_400_as_auth() -> None:
    message = (
        "Client error '400 Bad Request' for url "
        "'https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute?rpcids=wXbhsf'"
    )
    assert classify_notebooklm_error(message) == "auth"


def test_classify_notebooklm_error_detects_network_failures() -> None:
    assert classify_notebooklm_error("[Errno 11001] getaddrinfo failed") == "network"


def test_should_abort_notebooklm_bootstrap_aborts_auth_immediately() -> None:
    assert should_abort_notebooklm_bootstrap(
        "RPC Error 16: Authentication expired",
        consecutive_failures=1,
        max_failures=3,
    )


def test_should_abort_notebooklm_bootstrap_waits_until_network_limit() -> None:
    assert not should_abort_notebooklm_bootstrap(
        "[Errno 11001] getaddrinfo failed",
        consecutive_failures=1,
        max_failures=3,
    )
    assert should_abort_notebooklm_bootstrap(
        "[Errno 11001] getaddrinfo failed",
        consecutive_failures=3,
        max_failures=3,
    )
