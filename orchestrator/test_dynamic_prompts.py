import os
import sys
from dotenv import load_dotenv

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP_SERVER_DIR = os.path.join(WORKSPACE_ROOT, "mcp-server")
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

load_dotenv()

from agent import InfraGPTAgent

agent = InfraGPTAgent()

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
print(" RUNNING DYNAMIC SRE ENGINE ACCURACY VERIFICATION ")
print("==================================================")

for p in test_cases:
    print(f"\n[PROMPT]: {p}")
    tool_calls = []
    def on_t(name, args):
        tool_calls.append((name, args))
    
    resp = agent.send_message(p, on_tool_call=on_t)
    print(f" -> Tools Invoked: {tool_calls}")
    print(f" -> Response Snippet: {resp.splitlines()[0] if resp else 'None'}")
