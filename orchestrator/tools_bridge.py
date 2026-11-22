"""
Tool registry for the InfraGPT agent.

Calls are dispatched through the FastMCP client. This module does not import
the Kubernetes tool implementations.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Dict, List, Optional

from mcp_client import call_mcp_tool


def _call(name: str, args: Dict[str, Any]) -> Any:
    return call_mcp_tool(name, args)


def list_pods(namespace: str = "default") -> Any:
    """List pods in a namespace with health, readiness, restarts, and node."""
    return _call("list_pods", {"namespace": namespace})


def get_pod_logs(pod_name: str, namespace: str = "default", tail_lines: int = 100) -> Any:
    """Fetch recent logs from a pod."""
    return _call("get_pod_logs", {"pod_name": pod_name, "namespace": namespace, "tail_lines": tail_lines})


def get_pod_events(pod_name: str, namespace: str = "default") -> Any:
    """Fetch Kubernetes events for a pod."""
    return _call("get_pod_events", {"pod_name": pod_name, "namespace": namespace})


def describe_resource(resource_type: str, name: str, namespace: str = "default") -> Any:
    """Describe a pod or deployment."""
    return _call("describe_resource", {"resource_type": resource_type, "name": name, "namespace": namespace})


def list_deployments(namespace: str = "default") -> Any:
    """List deployments with replica counts and resource limits."""
    return _call("list_deployments", {"namespace": namespace})


def get_cluster_nodes() -> Any:
    """List cluster nodes and capacity."""
    return _call("get_cluster_nodes", {})


def scale_deployment(name: str, replicas: int, namespace: str = "default") -> Any:
    """Scale a deployment to a target replica count."""
    return _call("scale_deployment", {"name": name, "replicas": replicas, "namespace": namespace})


def patch_deployment_resources(
    name: str,
    memory_limit: Optional[str] = None,
    cpu_limit: Optional[str] = None,
    namespace: str = "default",
) -> Any:
    """Update CPU or memory limits for a deployment."""
    args: Dict[str, Any] = {"name": name, "namespace": namespace}
    if memory_limit is not None:
        args["memory_limit"] = memory_limit
    if cpu_limit is not None:
        args["cpu_limit"] = cpu_limit
    return _call("patch_deployment_resources", args)


def rollout_restart(deployment_name: str, namespace: str = "default") -> Any:
    """Rolling-restart a deployment."""
    return _call("rollout_restart", {"deployment_name": deployment_name, "namespace": namespace})


def delete_pod(pod_name: str, namespace: str = "default") -> Any:
    """Delete a pod."""
    return _call("delete_pod", {"pod_name": pod_name, "namespace": namespace})


def set_deployment_env(name: str, env_vars: Dict[str, str], namespace: str = "default") -> Any:
    """Set environment variables on a deployment."""
    return _call("set_deployment_env", {"name": name, "env_vars": env_vars, "namespace": namespace})


def set_deployment_image(
    name: str,
    image: str,
    container_name: Optional[str] = None,
    namespace: str = "default",
) -> Any:
    """Update a deployment container image."""
    args: Dict[str, Any] = {"name": name, "image": image, "namespace": namespace}
    if container_name is not None:
        args["container_name"] = container_name
    return _call("set_deployment_image", args)


AGENT_TOOLS = [
    list_pods,
    get_pod_logs,
    get_pod_events,
    describe_resource,
    list_deployments,
    get_cluster_nodes,
    scale_deployment,
    patch_deployment_resources,
    set_deployment_env,
    set_deployment_image,
    rollout_restart,
    delete_pod,
]

TOOL_MAP: Dict[str, Callable] = {tool.__name__: tool for tool in AGENT_TOOLS}


def execute_tool(tool_name: str, args: Dict[str, Any]) -> Any:
    """Execute a tool by name. Unknown names still go to the MCP server."""
    if tool_name not in TOOL_MAP and tool_name not in {"get_cluster_status", "apply_demo_scenario"}:
        return {"success": False, "error": "The operation could not be completed", "message": f"Tool '{tool_name}' is not available."}
    return _call(tool_name, args or {})


def get_k8s_adapter():
    """Compatibility helper for older tests. Runtime traffic uses the MCP client."""
    server_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp-server")
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    from k8s.client import get_k8s_adapter as _get

    return _get()
