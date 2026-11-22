"""
Kubernetes WRITE Tools Implementation for InfraGPT MCP Server.
⚠️ NOTE: These tools perform state-mutating operations and MUST be guarded
by the Human-in-the-Loop (HITL) approval gate in the Orchestrator layer.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .client import get_k8s_adapter


def scale_deployment_impl(name: str, replicas: int, namespace: str = "default") -> Dict[str, Any]:
    """Scale a deployment to a desired number of replica instances."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        dep = adapter.mock.deployments.get(namespace, {}).get(name)
        if not dep:
            return {
                "success": False,
                "error": "Deployment not found",
                "message": f"Deployment '{name}' was not found in namespace '{namespace}'.",
            }
        old_replicas = dep["replicas"]
        dep["replicas"] = replicas
        dep["available_replicas"] = replicas
        _sync_replica_pods(adapter, namespace, name, replicas)
        return {
            "success": True,
            "action": "scale_deployment",
            "deployment": name,
            "namespace": namespace,
            "previous_replicas": old_replicas,
            "new_replicas": replicas,
            "message": f"Successfully scaled deployment '{name}' from {old_replicas} to {replicas} replicas."
        }

    # Live Kubernetes Execution
    try:
        body = {"spec": {"replicas": replicas}}
        adapter.apps_v1.patch_namespaced_deployment_scale(
            name=name,
            namespace=namespace,
            body=body
        )
        return {
            "success": True,
            "action": "scale_deployment",
            "deployment": name,
            "namespace": namespace,
            "new_replicas": replicas,
            "message": f"Deployment '{name}' scale request submitted for {replicas} replicas."
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to scale deployment '{name}': {str(e)}"}


def patch_deployment_resources_impl(
    name: str,
    memory_limit: Optional[str] = None,
    cpu_limit: Optional[str] = None,
    namespace: str = "default"
) -> Dict[str, Any]:
    """Patch resource limits (RAM/CPU) for all containers in a deployment to resolve OOM or throttling."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        dep = adapter.mock.deployments.get(namespace, {}).get(name)
        if not dep:
            return {
                "success": False,
                "error": "Deployment not found",
                "message": f"Deployment '{name}' was not found in namespace '{namespace}'.",
            }

        old_mem = dep.get("memory_limit", "unspecified")
        old_cpu = dep.get("cpu_limit", "unspecified")
        if memory_limit:
            dep["memory_limit"] = memory_limit
        if cpu_limit:
            dep["cpu_limit"] = cpu_limit

        # If this was payment-service, simulate recovery!
        for pod in adapter.mock.pods.get(namespace, []):
            if pod.get("deployment") == name:
                pod["status"] = "Running"
                pod["ready"] = True
                pod["restarts"] = 0
                pod["logs"] += f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] INFO Restarted with new resource limits (Memory: {dep['memory_limit']}). Container is Healthy."
                pod["events"].append({
                    "type": "Normal",
                    "reason": "ResourcePatched",
                    "message": f"Patched resources: memory={memory_limit}, cpu={cpu_limit}. Pod healthy.",
                    "count": 1,
                    "last_seen": "just now"
                })
        dep["available_replicas"] = dep["replicas"]

        return {
            "success": True,
            "action": "patch_deployment_resources",
            "deployment": name,
            "namespace": namespace,
            "changes": {
                "memory_limit": {"old": old_mem, "new": memory_limit or old_mem},
                "cpu_limit": {"old": old_cpu, "new": cpu_limit or old_cpu}
            },
            "message": f"Successfully patched resources for '{name}'. Pods are restarting with updated limits."
        }

    # Live Kubernetes Execution
    try:
        limits = {}
        if memory_limit:
            limits["memory"] = memory_limit
        if cpu_limit:
            limits["cpu"] = cpu_limit

        patch_body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": name,
                                "resources": {"limits": limits}
                            }
                        ]
                    }
                }
            }
        }
        adapter.apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch_body)
        return {
            "success": True,
            "action": "patch_deployment_resources",
            "deployment": name,
            "namespace": namespace,
            "patched_limits": limits,
            "message": f"Applied resource patch to '{name}' in namespace '{namespace}'."
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to patch deployment resources: {str(e)}"}


def rollout_restart_impl(deployment_name: str, namespace: str = "default") -> Dict[str, Any]:
    """Perform a rolling restart of a deployment by updating its restart timestamp annotation."""
    adapter = get_k8s_adapter()
    now_str = datetime.now(timezone.utc).isoformat()

    if not adapter.is_live:
        dep = adapter.mock.deployments.get(namespace, {}).get(deployment_name)
        if not dep:
            return {
                "success": False,
                "error": "Deployment not found",
                "message": f"Deployment '{deployment_name}' was not found in namespace '{namespace}'.",
            }
        return {
            "success": True,
            "action": "rollout_restart",
            "deployment": deployment_name,
            "namespace": namespace,
            "restart_timestamp": now_str,
            "message": f"Successfully initiated rolling restart for deployment '{deployment_name}'."
        }

    # Live Kubernetes Execution
    try:
        patch_body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": now_str
                        }
                    }
                }
            }
        }
        adapter.apps_v1.patch_namespaced_deployment(name=deployment_name, namespace=namespace, body=patch_body)
        return {
            "success": True,
            "action": "rollout_restart",
            "deployment": deployment_name,
            "namespace": namespace,
            "message": f"Rolling restart triggered for '{deployment_name}'."
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to restart deployment '{deployment_name}': {str(e)}"}


def delete_pod_impl(pod_name: str, namespace: str = "default") -> Dict[str, Any]:
    """Delete a specific pod instance (Kubernetes Deployment controller will automatically recreate it)."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        pods = adapter.mock.pods.get(namespace, [])
        initial_len = len(pods)
        adapter.mock.pods[namespace] = [p for p in pods if p["name"] != pod_name]
        if len(adapter.mock.pods[namespace]) == initial_len:
            return {
                "success": False,
                "error": "Pod not found",
                "message": f"Pod '{pod_name}' was not found in namespace '{namespace}'.",
            }
        return {
            "success": True,
            "action": "delete_pod",
            "pod": pod_name,
            "namespace": namespace,
            "message": f"Pod '{pod_name}' deleted. Deployment controller will provision a fresh replica."
        }

    # Live Kubernetes Execution
    try:
        adapter.v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return {
            "success": True,
            "action": "delete_pod",
            "pod": pod_name,
            "namespace": namespace,
            "message": f"Pod '{pod_name}' deleted successfully."
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to delete pod '{pod_name}': {str(e)}"}


def set_deployment_env_impl(
    name: str,
    env_vars: Dict[str, str],
    namespace: str = "default"
) -> Dict[str, Any]:
    """Set or update environment variables for a deployment to resolve configuration crashes."""
    adapter = get_k8s_adapter()

    if not adapter.is_live:
        dep = adapter.mock.deployments.get(namespace, {}).get(name)
        if not dep:
            return {
                "success": False,
                "error": "Deployment not found",
                "message": f"Deployment '{name}' was not found in namespace '{namespace}'.",
            }
        dep.setdefault("env", {}).update(env_vars)
        _mark_recovered(adapter, namespace, name, f"Environment updated: {env_vars}")
        return {
            "success": True,
            "action": "set_deployment_env",
            "deployment": name,
            "namespace": namespace,
            "env_vars": env_vars,
            "message": f"Updated environment variables for '{name}'."
        }

    # Live Kubernetes Execution
    try:
        env_list = [{"name": k, "value": str(v)} for k, v in env_vars.items()]
        patch_body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": name,
                                "env": env_list
                            }
                        ]
                    }
                }
            }
        }
        adapter.apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch_body)
        return {
            "success": True,
            "action": "set_deployment_env",
            "deployment": name,
            "namespace": namespace,
            "updated_env": env_vars,
            "message": f"Successfully injected environment variables into '{name}'."
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to set env on '{name}': {str(e)}"}


def _mark_recovered(adapter, namespace: str, name: str, note: str) -> None:
    """Mark simulator pods for a deployment healthy after a successful write."""
    for pod in adapter.mock.pods.get(namespace, []):
        if pod.get("deployment") != name:
            continue
        pod["status"] = "Running"
        pod["ready"] = True
        pod["restarts"] = 0
        pod["last_exit_code"] = 0
        pod["exit_reason"] = None
        pod["logs"] = (pod.get("logs") or "") + f"\n[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] INFO {note}. Container is healthy."
        pod.setdefault("events", []).append({
            "type": "Normal",
            "reason": "Recovered",
            "message": note,
            "count": 1,
            "last_seen": "just now",
        })
    dep = adapter.mock.deployments.get(namespace, {}).get(name)
    if dep:
        dep["available_replicas"] = dep.get("replicas", 1)


def _sync_replica_pods(adapter, namespace: str, name: str, replicas: int) -> None:
    pods = adapter.mock.pods.setdefault(namespace, [])
    owned = [pod for pod in pods if pod.get("deployment") == name]
    rest = [pod for pod in pods if pod.get("deployment") != name]
    if not owned:
        owned = [{
            "name": f"{name}-00ab-new0",
            "deployment": name,
            "status": "Running",
            "ready": True,
            "restarts": 0,
            "age": "1m",
            "node": "minikube-node-01",
            "container_name": name,
            "last_exit_code": 0,
            "exit_reason": None,
            "logs": f"{name} replica started.",
            "events": [],
        }]
    while len(owned) < replicas:
        replica = dict(owned[0])
        replica["name"] = f"{name}-{len(owned):02d}ab-s{len(owned)}"
        replica["status"] = "Running"
        replica["ready"] = True
        replica["restarts"] = 0
        replica["age"] = "just now"
        replica["logs"] = f"Replica {replica['name']} started."
        replica["events"] = []
        owned.append(replica)
    if len(owned) > replicas:
        owned = owned[:replicas]
    adapter.mock.pods[namespace] = rest + owned


def set_deployment_image_impl(
    name: str,
    image: str,
    container_name: Optional[str] = None,
    namespace: str = "default"
) -> Dict[str, Any]:
    """Update container image tag on a deployment to resolve ImagePullBackOff or rollback."""
    adapter = get_k8s_adapter()
    target_container = container_name or name

    if not adapter.is_live:
        dep = adapter.mock.deployments.get(namespace, {}).get(name)
        if not dep:
            return {
                "success": False,
                "error": "Deployment not found",
                "message": f"Deployment '{name}' was not found in namespace '{namespace}'.",
            }
        dep["image"] = image
        _mark_recovered(adapter, namespace, name, f"Image updated to {image}")
        return {
            "success": True,
            "action": "set_deployment_image",
            "deployment": name,
            "image": image,
            "namespace": namespace,
            "message": f"Updated image for '{name}' to '{image}'."
        }

    # Live Kubernetes Execution
    try:
        patch_body = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": target_container,
                                "image": image
                            }
                        ]
                    }
                }
            }
        }
        adapter.apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch_body)
        return {
            "success": True,
            "action": "set_deployment_image",
            "deployment": name,
            "image": image,
            "namespace": namespace,
            "message": f"Successfully updated image for '{name}' to '{image}'."
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to set image on '{name}': {str(e)}"}


