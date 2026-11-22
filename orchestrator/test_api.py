"""
Automated Test Suite for InfraGPT FastAPI Backend
Verifies REST endpoints, chat routing, HITL approval lifecycle, and audit logs.
"""

import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "InfraGPT" in data["system"]


def test_cluster_status_endpoint():
    response = client.get("/api/cluster/status")
    assert response.status_code == 200
    data = response.json()
    assert "namespaces" in data
    assert "node_count" in data


def test_cluster_pods_endpoint():
    response = client.get("/api/cluster/pods?namespace=production")
    assert response.status_code == 200
    data = response.json()
    assert data["namespace"] == "production"
    assert len(data["pods"]) >= 3


def test_chat_diagnosis_flow():
    # Send a query asking about production issues
    payload = {"message": "What is wrong with the production namespace?", "namespace": "production"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["requires_approval"] is False
    assert "OOMKilled" in data["response"] or "payment-service" in data["response"]
    assert len(data["invoked_tools"]) >= 2


def test_hitl_approval_lifecycle():
    # 1. Ask for a scale action (which requires approval)
    payload = {"message": "Scale user-auth-service to 4 replicas", "namespace": "production"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["requires_approval"] is True
    assert "approval_id" in data
    approval_id = data["approval_id"]
    assert data["tool_name"] == "scale_deployment"

    # 2. Approve the action via /api/chat/approve
    approval_payload = {"approval_id": approval_id, "approved": True}
    approve_resp = client.post("/api/chat/approve", json=approval_payload)
    assert approve_resp.status_code == 200
    approve_data = approve_resp.json()
    assert approve_data["success"] is True
    assert approve_data["status"] == "EXECUTED"

    # 3. Verify audit log entry was created
    audit_resp = client.get("/api/audit/logs")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert len(audit_data["logs"]) > 0
    assert any(log["status"] == "APPROVED_AND_EXECUTED" for log in audit_data["logs"])


if __name__ == "__main__":
    print("[TEST] Running InfraGPT FastAPI Backend Tests...")
    test_root_endpoint()
    print("[PASS] Root Health Check Passed")
    test_cluster_status_endpoint()
    print("[PASS] Cluster Status Endpoint Passed")
    test_cluster_pods_endpoint()
    print("[PASS] Pods List Endpoint Passed")
    test_chat_diagnosis_flow()
    print("[PASS] Chat Diagnosis REST API Flow Passed")
    test_hitl_approval_lifecycle()
    print("[PASS] HITL Approval & Execution Lifecycle Passed")
    print("\n[SUCCESS] ALL FASTAPI BACKEND TESTS PASSED 100%!")
