"""
Unit Test Suite for InfraGPT Kubernetes MCP Tools
Verifies READ tools, diagnosis simulation, and WRITE tools.
"""

import pytest
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from k8s.client import get_k8s_adapter
from k8s.read_tools import (
    list_pods_impl,
    get_pod_logs_impl,
    get_pod_events_impl,
    describe_resource_impl,
    list_deployments_impl,
    get_cluster_nodes_impl
)
from k8s.write_tools import (
    scale_deployment_impl,
    patch_deployment_resources_impl,
    rollout_restart_impl,
    delete_pod_impl
)


def test_cluster_status():
    adapter = get_k8s_adapter()
    status = adapter.get_status()
    assert "mode" in status
    assert "namespaces" in status
    assert "default" in status["namespaces"]


def test_list_pods_production():
    pods = list_pods_impl(namespace="production")
    assert len(pods) >= 3
    # Check that payment-service pod is in CrashLoopBackOff for diagnosis testing
    payment_pod = next((p for p in pods if "payment-service" in p["name"]), None)
    assert payment_pod is not None
    assert payment_pod["status"] == "CrashLoopBackOff"
    assert payment_pod["ready"] is False
    assert payment_pod["is_healthy"] is False


def test_get_pod_logs():
    logs = get_pod_logs_impl("payment-service-7f8d9b-xc41", namespace="production")
    assert "OutOfMemoryError" in logs or "OOMKilled" in logs


def test_get_pod_events():
    events = get_pod_events_impl("payment-service-7f8d9b-xc41", namespace="production")
    assert len(events) > 0
    oom_event = next((e for e in events if e["reason"] == "OOMKilled"), None)
    assert oom_event is not None


def test_list_deployments():
    deps = list_deployments_impl(namespace="production")
    assert len(deps) >= 3
    names = [d["name"] for d in deps]
    assert "payment-service" in names
    assert "user-auth-service" in names


def test_scale_deployment():
    res = scale_deployment_impl("user-auth-service", replicas=5, namespace="production")
    assert res["success"] is True
    assert res["new_replicas"] == 5

    # Verify updated deployment
    deps = list_deployments_impl(namespace="production")
    auth_dep = next(d for d in deps if d["name"] == "user-auth-service")
    assert auth_dep["desired_replicas"] == 5


def test_patch_deployment_resources():
    res = patch_deployment_resources_impl(
        "payment-service",
        memory_limit="512Mi",
        namespace="production"
    )
    assert res["success"] is True
    assert res["changes"]["memory_limit"]["new"] == "512Mi"

    # Verify that pods recovered after patch
    pods = list_pods_impl(namespace="production")
    payment_pod = next(p for p in pods if "payment-service" in p["name"])
    assert payment_pod["status"] == "Running"
    assert payment_pod["is_healthy"] is True


if __name__ == "__main__":
    print("[TEST] Running InfraGPT MCP Tools Unit Tests...")
    test_cluster_status()
    print("[PASS] Cluster Status Check Passed")
    test_list_pods_production()
    print("[PASS] List Pods Check Passed")
    test_get_pod_logs()
    print("[PASS] Pod Logs Retrieval Passed")
    test_get_pod_events()
    print("[PASS] Pod Events Retrieval Passed")
    test_list_deployments()
    print("[PASS] List Deployments Passed")
    test_scale_deployment()
    print("[PASS] Scale Deployment Passed")
    test_patch_deployment_resources()
    print("[PASS] Patch Deployment Resources & Auto-Recovery Passed")
    print("\n[SUCCESS] ALL UNIT TESTS PASSED SUCCESSFULLY!")
