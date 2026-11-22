"""API coverage for the open InfraGPT issues."""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["INFRAGPT_K8S_MODE"] = "mock"
os.environ.pop("MCP_SERVER_URL", None)

from fastapi.testclient import TestClient

from app import app, pending_approvals
from errors import classify_exception
from tools_bridge import execute_tool


def test_staging_query_stays_a_read():
    """The namespace name 'staging' must not be read as an image-tag change."""
    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={"message": "Why is payment-service failing?", "namespace": "staging"},
    )
    body = response.json()
    assert body.get("requires_approval") is not True
    tools = [item.get("tool") for item in body.get("invoked_tools") or []]
    assert "set_deployment_image" not in tools
    assert "Deployment not found" in body["response"]


def test_friendly_labels():
    assert classify_exception(Exception("connection refused to 10.0.0.1"))[0] == "Kubernetes unavailable"
    assert classify_exception(Exception("Deployment 'payments' not found"))[0] == "Deployment not found"
    assert classify_exception(Exception("Pod 'x' not found"))[0] == "Pod not found"
    assert classify_exception(Exception("Approval expired"))[0] == "Approval expired"
    missing = execute_tool("scale_deployment", {"name": "does-not-exist", "replicas": 2, "namespace": "production"})
    assert missing["error"] == "Deployment not found"
    assert "Traceback" not in missing["message"]


def test_commands_rca_and_hitl():
    client = TestClient(app)

    health = client.get("/api/cluster/health", params={"namespace": "production"})
    assert health.status_code == 200
    assert health.json()["failing"] >= 1

    rca = client.post("/api/chat", json={"message": "Why is payment-service failing?", "namespace": "production"})
    body = rca.json()["response"]
    for heading in ("Root Cause", "Evidence", "Suggested Fix", "Risk Level"):
        assert heading in body
    assert "OOMKilled" in body or "Exit Code 137" in body

    ranked = client.post("/api/chat", json={"message": "Show pods with highest restarts", "namespace": "production"})
    assert "highest restarts" in ranked.json()["response"].lower()

    logs = client.post("/api/chat", json={"message": "Show logs of CrashLoop pods", "namespace": "production"})
    assert "CrashLoop" in logs.json()["response"]

    scale = client.post("/api/chat", json={"message": "Scale auth service to 4", "namespace": "production"})
    payload = scale.json()
    assert payload["requires_approval"] is True
    assert "→" in payload["summary"]
    assert payload["before"]["replicas"] != payload["after"]["replicas"]
    assert payload["after"]["replicas"] == 4

    approved = client.post("/api/chat/approve", json={"approval_id": payload["approval_id"], "approved": True})
    assert approved.status_code == 200
    assert approved.json()["success"] is True
    assert "Successfully" in approved.json()["message"]

    audit = client.get("/api/audit/logs")
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json()["logs"]]
    assert "scale_deployment" in actions or "chat_query" in actions

    status = client.get("/api/cluster/status")
    assert status.json()["last_command"]["text"]


def test_approval_expiry_and_demo():
    client = TestClient(app)
    scale = client.post("/api/chat", json={"message": "Restart frontend safely", "namespace": "production"})
    approval_id = scale.json()["approval_id"]
    pending_approvals[approval_id]["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    expired = client.post("/api/chat/approve", json={"approval_id": approval_id, "approved": True})
    assert expired.status_code == 410
    assert expired.json()["error"] == "Approval expired"

    demo = client.post("/api/demo/scenario", json={"scenario": "restore", "namespace": "production"})
    assert demo.status_code == 200
    assert demo.json()["success"] is True
    health = client.get("/api/cluster/health", params={"namespace": "production"})
    assert health.json()["failing"] == 0

    oom = client.post("/api/demo/scenario", json={"scenario": "oom", "namespace": "production"})
    assert oom.status_code == 200
    pods = client.get("/api/cluster/pods", params={"namespace": "production"}).json()["pods"]
    payment = next(pod for pod in pods if "payment-service" in pod["name"])
    assert payment["status"] == "CrashLoopBackOff"


if __name__ == "__main__":
    test_staging_query_stays_a_read()
    print("[PASS] Staging namespace does not become an image patch")
    test_friendly_labels()
    print("[PASS] Friendly errors")
    test_commands_rca_and_hitl()
    print("[PASS] RCA, commands, HITL, audit")
    test_approval_expiry_and_demo()
    print("[PASS] Expiry and demo scenarios")
