"""Plain-language errors for the API and the chat UI.

Stack traces stay in the server log. Callers receive a short label such as
"Kubernetes unavailable" or "Deployment not found".
"""

from __future__ import annotations

import logging

logger = logging.getLogger("infragpt-errors")

KNOWN_LABELS = {
    "Kubernetes unavailable",
    "Deployment not found",
    "Pod not found",
    "Approval expired",
    "Approval request not found",
    "Demo scenarios are disabled on live clusters",
    "The operation could not be completed",
}


def classify_exception(exc: BaseException) -> tuple[str, str]:
    """Map an exception or error string to a label and a sentence."""
    text = str(exc).strip()
    lowered = text.lower()

    if "approval expired" in lowered:
        return (
            "Approval expired",
            "This approval is no longer valid. Ask InfraGPT to propose the change again.",
        )
    if "approval request not found" in lowered or "already processed" in lowered:
        return (
            "Approval request not found",
            "This approval is no longer waiting. It may already have been approved or rejected.",
        )
    if "disabled on live clusters" in lowered:
        return (
            "Demo scenarios are disabled on live clusters",
            "OOM and CrashLoop buttons only change the built-in simulator. A live cluster is left untouched.",
        )
    if _is_connectivity(lowered):
        return (
            "Kubernetes unavailable",
            "The cluster API did not respond. InfraGPT is still running, and no change was applied.",
        )
    if "not found" in lowered and "pod" in lowered:
        return (
            "Pod not found",
            "That pod is not in the selected namespace.",
        )
    if "not found" in lowered:
        return (
            "Deployment not found",
            "That deployment is not in the selected namespace.",
        )

    if "traceback" in lowered or "stack" in lowered:
        return (
            "The operation could not be completed",
            "Something went wrong while talking to the cluster. No stack trace is shown.",
        )

    last_line = text.splitlines()[-1].strip() if text else ""
    if len(last_line) > 280:
        last_line = last_line[:280] + "…"
    return (
        "The operation could not be completed",
        last_line or "The request failed before it changed the cluster.",
    )


def _is_connectivity(lowered: str) -> bool:
    needles = (
        "connection refused",
        "connection reset",
        "timed out",
        "timeout",
        "unreachable",
        "name or service not known",
        "temporary failure",
        "max retries",
        "kubernetes unavailable",
        "failed to establish",
        "nodename nor servname",
        "network is unreachable",
        "mcp server",
        "all connection attempts failed",
        "connecterror",
    )
    return any(needle in lowered for needle in needles)


def normalize_tool_result(result):
    """Turn tool failures into {success, error, message} without tracebacks."""
    if isinstance(result, dict) and result.get("success") is False and result.get("error"):
        original = str(result.get("error"))
        label, message = classify_exception(Exception(original))
        if original in KNOWN_LABELS:
            label = original
        updated = dict(result)
        updated["error"] = label
        updated["message"] = result.get("message") or message
        return updated

    if (
        isinstance(result, list)
        and len(result) == 1
        and isinstance(result[0], dict)
        and "error" in result[0]
        and "name" not in result[0]
    ):
        label, message = classify_exception(Exception(str(result[0].get("error"))))
        return {"success": False, "error": label, "message": message}

    if isinstance(result, str) and result.lower().startswith("error"):
        label, message = classify_exception(Exception(result))
        return {"success": False, "error": label, "message": message}

    return result
