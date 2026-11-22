"""
Automated Integration Test for InfraGPT Orchestrator Agent
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import InfraGPTAgent
from tools_bridge import get_k8s_adapter


def test_agent_diagnosis_flow():
    agent = InfraGPTAgent()
    called_tools = []

    def on_tool(name, args):
        called_tools.append(name)

    # 1. Ask agent to diagnose issues
    resp = agent.send_message(
        "Check if there are any broken pods in production and tell me the root cause",
        on_tool_call=on_tool
    )

    print("[TEST] Agent Diagnosis Response Received:")
    print(resp)
    print("\n[TEST] Tools Invoked:", called_tools)

    assert "list_pods" in called_tools
    assert "get_pod_events" in called_tools
    assert "get_pod_logs" in called_tools
    assert "OOMKilled" in resp or "Exit Code 137" in resp
    assert "512Mi" in resp


def test_agent_patch_flow():
    agent = InfraGPTAgent()
    called_tools = []

    def on_tool(name, args):
        called_tools.append(name)

    # 2. Ask agent to patch memory
    resp = agent.send_message(
        "Yes please patch payment-service memory to 512Mi",
        approval_callback=lambda tool, args: True,  # Simulating user clicking 'Approve'
        on_tool_call=on_tool
    )

    print("\n[TEST] Agent Patch Response Received:")
    print(resp)
    assert "patch_deployment_resources" in called_tools
    assert "Successfully" in resp or "Applied" in resp


if __name__ == "__main__":
    print("[TEST] Starting Orchestrator Integration Tests...")
    test_agent_diagnosis_flow()
    print("[PASS] Autonomous Diagnostic RCA Flow Passed!")
    test_agent_patch_flow()
    print("[PASS] Patching & Auto-Remediation Flow Passed!")
    print("\n[SUCCESS] ORCHESTRATOR AGENT TESTS COMPLETED 100%!")
