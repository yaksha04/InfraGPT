"""
InfraGPT FastAPI Orchestrator Backend
Chat, cluster status, demo scenarios, and human approval for Kubernetes writes.
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import InfraGPTAgent
from audit_store import AuditStore
from errors import KNOWN_LABELS, classify_exception
from hitl import HITLApprovalGate
from mcp_client import mcp_status
from preview import build_operation_preview
from tools_bridge import execute_tool

logger = logging.getLogger("infragpt-api")

APPROVAL_TTL = timedelta(minutes=10)

app = FastAPI(
    title="InfraGPT Orchestrator API",
    description="Natural language Kubernetes manager with a human approval gate",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pending_approvals: Dict[str, Dict[str, Any]] = {}
audit = AuditStore()
agent = InfraGPTAgent()
last_command: Dict[str, Any] = {
    "text": "",
    "status": "idle",
    "at": None,
    "tool": None,
}


class ChatRequest(BaseModel):
    message: str = Field(..., description="Natural language prompt from the user")
    namespace: Optional[str] = Field("production", description="Active Kubernetes namespace")
    session_id: Optional[str] = Field("default", description="Conversation session id")
    history: Optional[List[Dict[str, Any]]] = Field(default=None)


class ApprovalRequest(BaseModel):
    approval_id: str
    approved: bool


class DemoRequest(BaseModel):
    scenario: str
    namespace: Optional[str] = "production"


def _target_of(args: Dict[str, Any]) -> str:
    return str(
        args.get("name")
        or args.get("pod_name")
        or args.get("deployment_name")
        or args.get("namespace")
        or "cluster"
    )


def log_audit_event(
    action: str,
    target: str,
    user: str,
    status: str,
    details: Dict[str, Any],
    session_id: Optional[str] = None,
) -> None:
    audit.add(
        {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "target": target,
            "user": user,
            "status": status,
            "details": details,
            "session_id": session_id,
        }
    )


def _remember_command(text: str, status: str, tool: Optional[str] = None) -> None:
    last_command.update(
        {
            "text": text,
            "status": status,
            "at": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
        }
    )


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _tool_payload(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict) and result.get("success") is False:
        return result
    return {"success": True, "result": result}


@app.exception_handler(HTTPException)
async def handle_http_exception(_request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "The operation could not be completed"
    if detail in KNOWN_LABELS:
        message = {
            "Approval expired": "This approval is no longer valid. Ask InfraGPT to propose the change again.",
            "Approval request not found": "This approval is no longer waiting.",
            "Kubernetes unavailable": "The cluster API did not respond. No change was applied.",
            "Deployment not found": "That deployment is not in the selected namespace.",
            "Pod not found": "That pod is not in the selected namespace.",
        }.get(detail, detail)
        return JSONResponse(status_code=exc.status_code, content={"error": detail, "message": message})
    label, message = classify_exception(Exception(detail))
    return JSONResponse(status_code=exc.status_code, content={"error": label, "message": message})


@app.exception_handler(Exception)
async def handle_unexpected(_request, exc: Exception):
    logger.exception("Unhandled API error")
    label, message = classify_exception(exc)
    return JSONResponse(status_code=500, content={"error": label, "message": message})


@app.get("/")
def root():
    return {
        "system": "InfraGPT Orchestrator Backend",
        "status": "online",
        "version": "1.1.0",
        "docs_url": "/docs",
        "audit_backend": audit.backend,
        "mcp": mcp_status(),
    }


@app.get("/api/cluster/status")
def get_cluster_status():
    status = execute_tool("get_cluster_status", {})
    if isinstance(status, dict) and status.get("success") is False:
        raise HTTPException(status_code=503, detail=status.get("error") or "Kubernetes unavailable")
    nodes = execute_tool("get_cluster_nodes", {})
    node_count = len(nodes) if isinstance(nodes, list) else 0
    return {
        **(status if isinstance(status, dict) else {}),
        "node_count": node_count,
        "ai_engine": "Gemini Live" if agent.is_live_llm else "SRE engine",
        "audit_backend": audit.backend,
        "audit_error": audit.last_error,
        "mcp": mcp_status(),
        "last_command": last_command,
    }


@app.get("/api/cluster/pods")
def get_pods(namespace: str = "production"):
    pods = execute_tool("list_pods", {"namespace": namespace})
    if isinstance(pods, dict) and pods.get("success") is False:
        raise HTTPException(status_code=503, detail=pods.get("error") or "Kubernetes unavailable")
    return {"namespace": namespace, "pods": pods}


@app.get("/api/cluster/deployments")
def get_deployments(namespace: str = "production"):
    deps = execute_tool("list_deployments", {"namespace": namespace})
    if isinstance(deps, dict) and deps.get("success") is False:
        raise HTTPException(status_code=503, detail=deps.get("error") or "Kubernetes unavailable")
    return {"namespace": namespace, "deployments": deps}


@app.get("/api/cluster/nodes")
def get_nodes():
    nodes = execute_tool("get_cluster_nodes", {})
    if isinstance(nodes, dict) and nodes.get("success") is False:
        raise HTTPException(status_code=503, detail=nodes.get("error") or "Kubernetes unavailable")
    return {"nodes": nodes}


@app.get("/api/cluster/health")
def get_health(namespace: str = "production"):
    pods = execute_tool("list_pods", {"namespace": namespace})
    if isinstance(pods, dict) and pods.get("success") is False:
        raise HTTPException(status_code=503, detail=pods.get("error") or "Kubernetes unavailable")
    if not isinstance(pods, list):
        pods = []
    total = len(pods)
    healthy = len([pod for pod in pods if pod.get("is_healthy")])
    restarts = sum(int(pod.get("restarts") or 0) for pod in pods)
    score = 100 if total == 0 else max(0, round((healthy / total) * 100) - min(25, restarts))
    if total == 0:
        grade = "No workloads"
    elif score >= 90:
        grade = "Healthy"
    elif score >= 60:
        grade = "Degraded"
    else:
        grade = "Critical"
    return {
        "namespace": namespace,
        "score": score,
        "grade": grade,
        "healthy": healthy,
        "failing": total - healthy,
        "restarts": restarts,
        "total": total,
    }


@app.get("/api/audit/logs")
def get_audit_trail():
    return {"logs": audit.list(), "backend": audit.backend}


@app.get("/api/demo/scenarios")
def list_scenarios():
    return {
        "scenarios": [
            {
                "id": "oom",
                "title": "Trigger OOM",
                "detail": "Puts payment-service into CrashLoopBackOff with a 128Mi limit and exit code 137.",
            },
            {
                "id": "crashloop",
                "title": "Trigger CrashLoop",
                "detail": "Removes REDIS_HOST from order-service so it crash-loops on boot.",
            },
            {
                "id": "restore",
                "title": "Restore Healthy State",
                "detail": "Returns the simulator workloads to running replicas with safe limits and config.",
            },
        ]
    }


@app.post("/api/demo/scenario")
def run_demo(req: DemoRequest):
    namespace = req.namespace or "production"
    result = execute_tool("apply_demo_scenario", {"scenario": req.scenario, "namespace": namespace})
    ok = not (isinstance(result, dict) and result.get("success") is False)
    _remember_command(f"Demo: {req.scenario}", "EXECUTED" if ok else "FAILED", "apply_demo_scenario")
    log_audit_event(
        action="apply_demo_scenario",
        target=namespace,
        user="Engineer (Web UI)",
        status="EXECUTED" if ok else "FAILED",
        details={"scenario": req.scenario, "result": result},
    )
    if not ok:
        raise HTTPException(status_code=400, detail=result.get("error") or "The operation could not be completed")
    return result


@app.post("/api/chat")
def handle_chat_message(req: ChatRequest):
    invoked_tools: List[Dict[str, Any]] = []

    def on_tool(name: str, args: Dict[str, Any]):
        invoked_tools.append({"tool": name, "args": args})

    pending_action = None
    blocked = None

    def intercept_approval(tool_name: str, args: Dict[str, Any]) -> bool:
        nonlocal pending_action, blocked
        preview = build_operation_preview(tool_name, args)
        if preview.get("blocked"):
            blocked = preview
            return False
        approval_id = str(uuid.uuid4())
        created = datetime.now(timezone.utc)
        pending_action = {
            "approval_id": approval_id,
            "tool_name": tool_name,
            "args": args,
            "description": HITLApprovalGate.format_approval_request(tool_name, args),
            "summary": preview.get("summary"),
            "before": preview.get("before"),
            "after": preview.get("after"),
            "risk": preview.get("risk"),
            "created_at": created.isoformat(),
            "expires_at": (created + APPROVAL_TTL).isoformat(),
        }
        pending_approvals[approval_id] = pending_action
        return False

    formatted_prompt = f"[Active Dashboard Namespace: {req.namespace}]\nEngineer Query: {req.message}"
    try:
        response_text = agent.send_message(
            user_prompt=formatted_prompt,
            approval_callback=intercept_approval,
            on_tool_call=on_tool,
            history=req.history,
        )
    except Exception as exc:
        label, message = classify_exception(exc)
        logger.exception("Chat failed")
        _remember_command(req.message, "FAILED")
        return {
            "requires_approval": False,
            "response": f"**{label}**\n\n{message}",
            "error": label,
            "invoked_tools": invoked_tools,
        }

    if blocked and not pending_action:
        log_audit_event(
            action="blocked_write",
            target=req.namespace or "production",
            user="Engineer (Web UI)",
            status="FAILED",
            details={"query": req.message, "error": blocked.get("error")},
            session_id=req.session_id,
        )
        _remember_command(req.message, "FAILED")
        return {
            "requires_approval": False,
            "response": f"**{blocked.get('error')}**\n\n{blocked.get('message')}",
            "error": blocked.get("error"),
            "invoked_tools": invoked_tools,
        }

    if pending_action:
        log_audit_event(
            action=pending_action["tool_name"],
            target=_target_of(pending_action["args"]),
            user="Engineer (Web UI)",
            status="PENDING_APPROVAL",
            details={
                "args": pending_action["args"],
                "summary": pending_action.get("summary"),
                "before": pending_action.get("before"),
                "after": pending_action.get("after"),
            },
            session_id=req.session_id,
        )
        _remember_command(pending_action.get("summary") or req.message, "PENDING_APPROVAL", pending_action["tool_name"])
        return {
            "requires_approval": True,
            "approval_id": pending_action["approval_id"],
            "tool_name": pending_action["tool_name"],
            "args": pending_action["args"],
            "summary": pending_action.get("summary"),
            "before": pending_action.get("before"),
            "after": pending_action.get("after"),
            "risk": pending_action.get("risk"),
            "expires_at": pending_action.get("expires_at"),
            "message": response_text,
            "invoked_tools": invoked_tools,
        }

    log_audit_event(
        action="chat_query",
        target=req.namespace or "production",
        user="Engineer (Web UI)",
        status="EXECUTED",
        details={"query": req.message, "tools": [item["tool"] for item in invoked_tools]},
        session_id=req.session_id,
    )
    _remember_command(req.message, "EXECUTED", invoked_tools[-1]["tool"] if invoked_tools else None)
    return {
        "requires_approval": False,
        "response": response_text,
        "invoked_tools": invoked_tools,
    }


@app.post("/api/chat/approve")
def handle_approval_action(req: ApprovalRequest):
    pending = pending_approvals.get(req.approval_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Approval request not found")

    expires_at = pending.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > _parse_time(expires_at):
        pending_approvals.pop(req.approval_id, None)
        log_audit_event(
            action=pending["tool_name"],
            target=_target_of(pending["args"]),
            user="Engineer (Web UI)",
            status="EXPIRED",
            details=pending["args"],
        )
        _remember_command(pending.get("summary") or pending["tool_name"], "EXPIRED", pending["tool_name"])
        raise HTTPException(status_code=410, detail="Approval expired")

    tool_name = pending["tool_name"]
    args = pending["args"]
    summary = pending.get("summary") or tool_name

    if not req.approved:
        pending_approvals.pop(req.approval_id, None)
        log_audit_event(
            action=tool_name,
            target=_target_of(args),
            user="Engineer (Web UI)",
            status="REJECTED_BY_USER",
            details={"args": args, "summary": summary},
        )
        _remember_command(summary, "REJECTED", tool_name)
        return {
            "success": False,
            "status": "REJECTED",
            "tool_name": tool_name,
            "summary": summary,
            "message": f"Rejected. {summary} was not applied.",
        }

    result = execute_tool(tool_name, args)
    pending_approvals.pop(req.approval_id, None)
    failed = isinstance(result, dict) and result.get("success") is False
    status = "FAILED" if failed else "APPROVED_AND_EXECUTED"
    log_audit_event(
        action=tool_name,
        target=_target_of(args),
        user="Engineer (Web UI)",
        status=status,
        details={"args": args, "summary": summary, "result": result},
    )
    _remember_command(summary, status, tool_name)

    if failed:
        return {
            "success": False,
            "status": "FAILED",
            "tool_name": tool_name,
            "summary": summary,
            "before": pending.get("before"),
            "after": pending.get("after"),
            "error": result.get("error"),
            "message": result.get("message") or result.get("error") or "The change failed.",
            "result": result,
        }

    return {
        "success": True,
        "status": "EXECUTED",
        "tool_name": tool_name,
        "summary": summary,
        "before": pending.get("before"),
        "after": pending.get("after"),
        "risk": pending.get("risk"),
        "result": result,
        "message": f"Successfully applied: {summary}.",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ORCHESTRATOR_PORT", "8888"))
    print(f"Starting InfraGPT on http://127.0.0.1:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
