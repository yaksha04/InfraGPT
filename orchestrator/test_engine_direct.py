import os
import sys

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP_SERVER_DIR = os.path.join(WORKSPACE_ROOT, "mcp-server")
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

from agent import InfraGPTAgent

agent = InfraGPTAgent(api_key="none")

test_cases = [
    "now patch memory of inventory service from 512Mi to 256Mi",
    "now patch memory of payment service from 512Mi to 256Mi",
    "fix inventory service missing database environment",
    "scale payment-service to 4 replicas",
    "scale user-auth-service to 5 replicas",
    "What is wrong with inventory-service?",
    "What is wrong with payment-service?"
]

print("==================================================")
print(" RUNNING ZERO-HARDCODED DYNAMIC SRE ENGINE TESTS  ")
print("==================================================")

for p in test_cases:
    tool_calls = []
    def on_t(name, args):
        tool_calls.append((name, args))
    
    resp = agent._simulated_agent_response(p, approval_callback=None, on_tool_call=on_t)
    print(f"\n[PROMPT]: {p}")
    print(f" -> Tool Invoked: {tool_calls}")
    for line in resp.splitlines()[:3]:
        if line.strip():
            print(f"    {line}")
