import os
import sys
from dotenv import load_dotenv

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP_SERVER_DIR = os.path.join(WORKSPACE_ROOT, "mcp-server")
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)

load_dotenv()

from k8s.client import get_k8s_adapter

adapter = get_k8s_adapter()
print("Adapter is_live:", adapter.is_live)
print("Adapter status:", adapter.get_status())
