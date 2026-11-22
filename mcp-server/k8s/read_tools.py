"""
Kubernetes READ Tools Implementation for InfraGPT MCP Server.
These tools are safe for direct execution without requiring explicit human-in-the-loop approval.
"""

from typing import List, Dict, Any, Optional
from .client import get_k8s_adapter


def list_pods_impl(namespace: str = "default") -> List[Dict[str, Any]]:
    """List all pods in a given namespace with readiness, restart count, and health status."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        pods = adapter.mock.pods.get(namespace, [])
        return [
            {
                "name": p["name"],
                "namespace": namespace,
                "status": p["status"],
                "ready": p["ready"],
                "restarts": p["restarts"],
                "age": p["age"],
                "node": p["node"],
                "container": p["container_name"],
                "is_healthy": p["status"] == "Running" and p["ready"]
            }
            for p in pods
        ]

    # Live Kubernetes Execution
    try:
        pod_list = adapter.v1.list_namespaced_pod(namespace=namespace)
        result = []
        for p in pod_list.items:
            container_statuses = p.status.container_statuses or []
            is_ready = all(c.ready for c in container_statuses) if container_statuses else False
            restart_count = sum(c.restart_count for c in container_statuses)
            phase = p.status.phase

            # Detect CrashLoopBackOff or OOMKilled in container statuses
            for c in container_statuses:
                if c.state and c.state.waiting and c.state.waiting.reason:
                    phase = c.state.waiting.reason
                elif c.state and c.state.terminated and c.state.terminated.reason:
                    phase = c.state.terminated.reason

            result.append({
                "name": p.metadata.name,
                "namespace": namespace,
                "status": phase,
                "ready": is_ready,
                "restarts": restart_count,
                "age": str(p.metadata.creation_timestamp),
                "node": p.spec.node_name or "unassigned",
                "is_healthy": phase == "Running" and is_ready
            })
        return result
    except Exception as e:
        return [{"error": f"Failed to list pods in namespace '{namespace}': {str(e)}"}]


def get_pod_logs_impl(pod_name: str, namespace: str = "default", tail_lines: int = 100) -> str:
    """Retrieve the recent stdout/stderr log output from a specified pod."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        for p in adapter.mock.pods.get(namespace, []):
            if p["name"] == pod_name or pod_name in p["name"]:
                return p.get("logs", f"No logs recorded for pod {pod_name}")
        return f"Error: Pod '{pod_name}' not found in namespace '{namespace}'."

    # Live Kubernetes Execution
    try:
        logs = adapter.v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines
        )
        return logs or "(Log stream empty)"
    except Exception as e:
        return f"Error fetching logs for pod '{pod_name}' in namespace '{namespace}': {str(e)}"


def get_pod_events_impl(pod_name: str, namespace: str = "default") -> List[Dict[str, Any]]:
    """Retrieve Kubernetes cluster events related to a specific pod (useful for CrashLoop, OOMKilled, Eviction diagnosis)."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        for p in adapter.mock.pods.get(namespace, []):
            if p["name"] == pod_name or pod_name in p["name"]:
                return p.get("events", [])
        return [{"error": f"Pod '{pod_name}' not found in namespace '{namespace}'."}]

    # Live Kubernetes Execution
    try:
        events = adapter.v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}"
        )
        return [
            {
                "type": e.type,
                "reason": e.reason,
                "message": e.message,
                "count": e.count or 1,
                "first_timestamp": str(e.first_timestamp),
                "last_timestamp": str(e.last_timestamp)
            }
            for e in events.items
        ]
    except Exception as e:
        return [{"error": f"Failed to fetch events for pod '{pod_name}': {str(e)}"}]


def describe_resource_impl(resource_type: str, name: str, namespace: str = "default") -> Dict[str, Any]:
    """Retrieve detailed metadata, specifications, and status of a Kubernetes resource (pod, deployment, service)."""
    adapter = get_k8s_adapter()
    r_type = resource_type.lower().strip()

    if not adapter.is_live:
        if r_type in ["deployment", "deploy"]:
            dep = adapter.mock.deployments.get(namespace, {}).get(name)
            if dep:
                return {"resource_type": "Deployment", "name": name, "namespace": namespace, "spec": dep}
        elif r_type in ["pod", "po"]:
            for p in adapter.mock.pods.get(namespace, []):
                if p["name"] == name:
                    return {"resource_type": "Pod", "name": name, "namespace": namespace, "spec": p}
        return {"error": f"Resource {resource_type}/{name} not found in namespace '{namespace}'."}

    # Live Kubernetes Execution
    try:
        if r_type in ["pod", "po"]:
            obj = adapter.v1.read_namespaced_pod(name=name, namespace=namespace)
            return {
                "name": obj.metadata.name,
                "namespace": obj.metadata.namespace,
                "node": obj.spec.node_name,
                "status": obj.status.phase,
                "containers": [{"name": c.name, "image": c.image} for c in obj.spec.containers]
            }
        elif r_type in ["deployment", "deploy"]:
            obj = adapter.apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
            return {
                "name": obj.metadata.name,
                "namespace": obj.metadata.namespace,
                "replicas": obj.spec.replicas,
                "available_replicas": obj.status.available_replicas or 0,
                "strategy": obj.spec.strategy.type
            }
        else:
            return {"error": f"Unsupported resource type '{resource_type}'. Supported: pod, deployment."}
    except Exception as e:
        return {"error": f"Failed to describe {resource_type}/{name}: {str(e)}"}


def list_deployments_impl(namespace: str = "default") -> List[Dict[str, Any]]:
    """List all deployments in a namespace with their desired vs available replica counts."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        deps = adapter.mock.deployments.get(namespace, {})
        return [
            {
                "name": name,
                "namespace": namespace,
                "desired_replicas": data["replicas"],
                "available_replicas": data["available_replicas"],
                "image": data["image"],
                "memory_limit": data["memory_limit"],
                "cpu_limit": data["cpu_limit"]
            }
            for name, data in deps.items()
        ]

    # Live Kubernetes Execution
    try:
        deps = adapter.apps_v1.list_namespaced_deployment(namespace=namespace)
        return [
            {
                "name": d.metadata.name,
                "namespace": namespace,
                "desired_replicas": d.spec.replicas,
                "available_replicas": d.status.available_replicas or 0,
                "updated_replicas": d.status.updated_replicas or 0,
                "images": [c.image for c in d.spec.template.spec.containers]
            }
            for d in deps.items
        ]
    except Exception as e:
        return [{"error": f"Failed to list deployments in namespace '{namespace}': {str(e)}"}]


def get_cluster_nodes_impl() -> List[Dict[str, Any]]:
    """Get the list of cluster nodes, their health status, and capacity."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        return adapter.mock.nodes

    # Live Kubernetes Execution
    try:
        node_list = adapter.v1.list_node()
        return [
            {
                "name": n.metadata.name,
                "status": "Ready" if any(c.type == "Ready" and c.status == "True" for c in n.status.conditions) else "NotReady",
                "kubelet_version": n.status.node_info.kubelet_version,
                "cpu_capacity": n.status.capacity.get("cpu"),
                "memory_capacity": n.status.capacity.get("memory")
            }
            for n in node_list.items
        ]
    except Exception as e:
        return [{"error": f"Failed to fetch cluster nodes: {str(e)}"}]
