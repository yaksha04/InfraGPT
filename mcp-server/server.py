"""
InfraGPT Kubernetes MCP Server
Exposes Kubernetes operations as Model Context Protocol (MCP) tools for LLM agent interaction.
"""

import sys
import os
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP

# Add parent directory to path so imports work seamlessly
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
    delete_pod_impl,
    set_deployment_env_impl,
    set_deployment_image_impl,
)
from k8s.scenarios import apply_demo_scenario_impl

# Initialize FastMCP Server
mcp = FastMCP("InfraGPT-K8s-Server")


# ============================================================================
# 🟢 READ TOOLS (Inspection, Diagnosis & Metrics - Safe for Auto-Execution)
# ============================================================================

@mcp.tool()
def get_cluster_status() -> Dict[str, Any]:
    """Get the current operational status of the Kubernetes cluster, connection mode (live vs mock), and available namespaces."""
    adapter = get_k8s_adapter()
    return adapter.get_status()


@mcp.tool()
def list_pods(namespace: str = "default") -> List[Dict[str, Any]]:
    """List all pods in a specified namespace with their health status, readiness, restart count, and node assignment.
    
    Args:
        namespace: The Kubernetes namespace to inspect (e.g., 'default', 'production', 'kube-system').
    """
    return list_pods_impl(namespace=namespace)


@mcp.tool()
def get_pod_logs(pod_name: str, namespace: str = "default", tail_lines: int = 100) -> str:
    """Fetch stdout and stderr logs from a pod to diagnose crashes, errors, or application runtime issues.
    
    Args:
        pod_name: Name or prefix of the target pod.
        namespace: The namespace where the pod lives.
        tail_lines: Number of recent log lines to retrieve (default: 100).
    """
    return get_pod_logs_impl(pod_name=pod_name, namespace=namespace, tail_lines=tail_lines)


@mcp.tool()
def get_pod_events(pod_name: str, namespace: str = "default") -> List[Dict[str, Any]]:
    """Fetch recent Kubernetes cluster warning and lifecycle events for a pod (crucial for identifying OOMKilled, BackOff, and Evictions).
    
    Args:
        pod_name: Name of the pod to get events for.
        namespace: The namespace where the pod lives.
    """
    return get_pod_events_impl(pod_name=pod_name, namespace=namespace)


@mcp.tool()
def describe_resource(resource_type: str, name: str, namespace: str = "default") -> Dict[str, Any]:
    """Inspect detailed spec, configuration, and runtime status of a Kubernetes resource.
    
    Args:
        resource_type: Type of resource ('pod' or 'deployment').
        name: Name of the resource.
        namespace: Target namespace.
    """
    return describe_resource_impl(resource_type=resource_type, name=name, namespace=namespace)


@mcp.tool()
def list_deployments(namespace: str = "default") -> List[Dict[str, Any]]:
    """List all deployments in a namespace along with desired vs available replica counts and configured resource limits.
    
    Args:
        namespace: Target namespace to query.
    """
    return list_deployments_impl(namespace=namespace)


@mcp.tool()
def get_cluster_nodes() -> List[Dict[str, Any]]:
    """List all physical/virtual nodes in the Kubernetes cluster along with health status, CPU, and Memory capacity."""
    return get_cluster_nodes_impl()


# ============================================================================
# 🔴 WRITE TOOLS (State-Mutating Operations - Require HITL Human Approval)
# ============================================================================

@mcp.tool()
def scale_deployment(name: str, replicas: int, namespace: str = "default") -> Dict[str, Any]:
    """⚠️ WRITE OPERATION: Scale a deployment up or down to handle load changes.
    
    Args:
        name: Name of the deployment (e.g., 'payment-service').
        replicas: Target number of replica pod instances (e.g., 3).
        namespace: Namespace containing the deployment.
    """
    return scale_deployment_impl(name=name, replicas=replicas, namespace=namespace)


@mcp.tool()
def patch_deployment_resources(
    name: str,
    memory_limit: Optional[str] = None,
    cpu_limit: Optional[str] = None,
    namespace: str = "default"
) -> Dict[str, Any]:
    """⚠️ WRITE OPERATION: Update CPU or Memory limits for a deployment container to remediate Out-Of-Memory (OOM) or CPU throttling.
    
    Args:
        name: Name of the deployment.
        memory_limit: New memory limit string (e.g., '512Mi', '1Gi').
        cpu_limit: New CPU limit string (e.g., '500m', '1').
        namespace: Target namespace.
    """
    return patch_deployment_resources_impl(
        name=name,
        memory_limit=memory_limit,
        cpu_limit=cpu_limit,
        namespace=namespace
    )


@mcp.tool()
def rollout_restart(deployment_name: str, namespace: str = "default") -> Dict[str, Any]:
    """⚠️ WRITE OPERATION: Trigger a rolling restart of all pods in a deployment with zero downtime.
    
    Args:
        deployment_name: Name of the deployment to restart.
        namespace: Target namespace.
    """
    return rollout_restart_impl(deployment_name=deployment_name, namespace=namespace)


@mcp.tool()
def delete_pod(pod_name: str, namespace: str = "default") -> Dict[str, Any]:
    """⚠️ WRITE OPERATION: Force delete a stuck pod so the Deployment controller can recreate a clean replica.
    
    Args:
        pod_name: Exact name of the pod to delete.
        namespace: Target namespace.
    """
    return delete_pod_impl(pod_name=pod_name, namespace=namespace)


@mcp.tool()
def set_deployment_env(name: str, env_vars: Dict[str, str], namespace: str = "default") -> Dict[str, Any]:
    """⚠️ WRITE OPERATION: Set environment variables on a deployment.

    Args:
        name: Deployment name.
        env_vars: Environment variables to set.
        namespace: Target namespace.
    """
    return set_deployment_env_impl(name=name, env_vars=env_vars, namespace=namespace)


@mcp.tool()
def set_deployment_image(
    name: str,
    image: str,
    container_name: Optional[str] = None,
    namespace: str = "default",
) -> Dict[str, Any]:
    """⚠️ WRITE OPERATION: Change a deployment container image.

    Args:
        name: Deployment name.
        image: New image tag.
        container_name: Container to update. Defaults to the deployment name.
        namespace: Target namespace.
    """
    return set_deployment_image_impl(
        name=name,
        image=image,
        container_name=container_name,
        namespace=namespace,
    )


@mcp.tool()
def apply_demo_scenario(scenario: str, namespace: str = "production") -> Dict[str, Any]:
    """Apply a simulator-only demo: oom, crashloop, or restore.

    Args:
        scenario: One of oom, crashloop, restore.
        namespace: Namespace to mutate inside the simulator.
    """
    return apply_demo_scenario_impl(scenario=scenario, namespace=namespace)


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport in {"http", "streamable-http"}:
        host = os.getenv("FASTMCP_HOST", "0.0.0.0")
        port = int(os.getenv("FASTMCP_PORT", os.getenv("MCP_SERVER_PORT", "8000")))
        print(f"Starting InfraGPT FastMCP server on http://{host}:{port}/mcp")
        mcp.run(transport="http", host=host, port=port, stateless_http=True)
    else:
        print("Starting InfraGPT Kubernetes FastMCP server on stdio...")
        mcp.run()
