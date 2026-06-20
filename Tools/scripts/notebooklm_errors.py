from __future__ import annotations

from typing import Literal

NotebookLmErrorKind = Literal["auth", "network", "other"]

_AUTH_MARKERS = (
    "authentication expired",
    "rpc error 16",
    "client error '400 bad request'",
    "https://notebooklm.google.com/_/labstailwindui/data/batchexecute",
)

_NETWORK_MARKERS = (
    "handshake operation timed out",
    "read operation timed out",
    "getaddrinfo failed",
    "forcibly closed by the remote host",
    "server disconnected without sending a response",
    "connection reset by peer",
    "peer closed connection",
    "incomplete chunked read",
    "incomplete message body",
    "remote end closed connection",
)


def _normalize_error_text(text: str) -> str:
    return " ".join(text.casefold().split())



def classify_notebooklm_error(text: str) -> NotebookLmErrorKind:
    normalized = _normalize_error_text(text)
    if any(marker in normalized for marker in _AUTH_MARKERS):
        return "auth"
    if any(marker in normalized for marker in _NETWORK_MARKERS):
        return "network"
    return "other"



def should_abort_notebooklm_bootstrap(
    text: str,
    *,
    consecutive_failures: int,
    max_failures: int,
) -> bool:
    kind = classify_notebooklm_error(text)
    if kind == "auth":
        return True
    if kind == "network":
        return consecutive_failures >= max_failures
    return False
