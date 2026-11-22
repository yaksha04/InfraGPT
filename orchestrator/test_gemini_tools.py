import os
import sys
from dotenv import load_dotenv

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP_SERVER_DIR = os.path.join(WORKSPACE_ROOT, "mcp-server")
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

load_dotenv()

from agent import InfraGPTAgent

agent = InfraGPTAgent(model_name="gemini-2.5-flash")

prompts = [
    "now patch memory of inventory service from 512Mi to 256Mi",
    "scale payment-service to 3 replicas",
    "why is inventory-service crashing in production?",
    "fix inventory service missing database environment"
]

for p in prompts:
    print(f"\n====================\nPROMPT: {p}")
    resp = agent.send_message(p)
    print("RESPONSE:\n", resp)
