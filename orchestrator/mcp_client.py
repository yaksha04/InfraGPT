"""MCP client used by the orchestrator.

Every Kubernetes tool call goes through FastMCP. When MCP_SERVER_URL is set,
the client uses the streamable HTTP server. Otherwise it attaches an in-process
FastMCP client to the same server object, which keeps local runs to one process.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from typing import Any

from errors import classify_exception, normalize_tool_result

logger = logging.getLogger("infragpt-mcp")

_LOCK = threading.RLock()
_STATUS: dict[str, str] = {"mode": "not-connected", "detail": ""}


def mcp_status() -> dict[str, str]:
    return dict(_STATUS)


def _server_dir() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "mcp-server")


def _unwrap(result: Any) -> Any:
    """Prefer structured MCP content. List tools come back wrapped as {"result": [...]}."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict) and structured:
        if set(structured.keys()) == {"result"}:
            return structured["result"]
        return structured

    data = getattr(result, "data", None)
    if data is not None and not _empty_root_list(data):
        return data

    content = getattr(result, "content", None) or []
    texts = []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    if len(texts) == 1:
        import json
        try:
            return json.loads(texts[0])
        except json.JSONDecodeError:
            return texts[0]
    if texts:
        return "\n".join(texts)
    return data


def _empty_root_list(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return type(value[0]).__name__ == "Root" and not hasattr(value[0], "model_dump")


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value


async def _call(url: str | None, name: str, arguments: dict[str, Any]) -> Any:
    if url:
        from fastmcp import Client

        async with Client(url, timeout=20) as client:
            result = await client.call_tool(name, arguments, raise_on_error=False)
            if getattr(result, "is_error", False):
                message = _unwrap(result) or "Tool call failed"
                raise RuntimeError(str(message))
            return _plain(_unwrap(result))

    server_dir = _server_dir()
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    from server import mcp

    tool = await mcp.get_tool(name)
    return _plain(tool.fn(**arguments))


def call_mcp_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    args = dict(arguments or {})
    url = os.getenv("MCP_SERVER_URL", "").strip() or None
    with _LOCK:
        try:
            if url:
                _STATUS.update(mode="http", detail=url)
            else:
                _STATUS.update(mode="in-process", detail="FastMCP tool registry")
            result = asyncio.run(_call(url, name, args))
        except Exception as exc:
            label, message = classify_exception(exc)
            if label == "The operation could not be completed" and url:
                label = "Kubernetes unavailable"
                message = "InfraGPT could not reach the MCP server that talks to Kubernetes."
            _STATUS.update(mode="error", detail=label)
            logger.warning("MCP tool %s failed: %s", name, exc)
            return {"success": False, "error": label, "message": message}
    return normalize_tool_result(result)
