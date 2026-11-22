"""Before/after summaries for the human approval gate."""

from __future__ import annotations

from typing import Any

from tools_bridge import execute_tool


def _blocked(error: str, message: str) -> dict[str, Any]:
    return {"blocked": True, "error": error, "message": message}


def _deployments(namespace: str):
    data = execute_tool("list_deployments", {"namespace": namespace})
    if isinstance(data, dict) and data.get("success") is False:
        return None, data
    if not isinstance(data, list):
        return None, _blocked("Kubernetes unavailable", "Deployment list was not returned.")
    return data, None


def _pods(namespace: str):
    data = execute_tool("list_pods", {"namespace": namespace})
    if isinstance(data, dict) and data.get("success") is False:
        return None, data
    if not isinstance(data, list):
        return None, _blocked("Kubernetes unavailable", "Pod list was not returned.")
    return data, None


def _find_deployment(name: str, namespace: str):
    deps, error = _deployments(namespace)
    if error:
        return None, error if error.get("blocked") else _blocked(error.get("error", "Kubernetes unavailable"), error.get("message", ""))
    match = next((item for item in deps if item.get("name") == name), None)
    if not match:
        return None, _blocked(
            "Deployment not found",
            f"Deployment '{name}' was not found in namespace '{namespace}'.",
        )
    return match, None


def build_operation_preview(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    namespace = args.get("namespace") or "default"

    if tool_name == "scale_deployment":
        name = args.get("name") or ""
        replicas = int(args.get("replicas") or 0)
        current, error = _find_deployment(name, namespace)
        if error:
            return error
        before = int(current.get("desired_replicas") or 0)
        delta = abs(replicas - before)
        risk = "High" if replicas == 0 or delta >= 5 else "Medium"
        return {
            "blocked": False,
            "summary": f"Scale {name} from {before} → {replicas} replicas",
            "before": {"deployment": name, "namespace": namespace, "replicas": before},
            "after": {"deployment": name, "namespace": namespace, "replicas": replicas},
            "risk": risk,
        }

    if tool_name == "patch_deployment_resources":
        name = args.get("name") or ""
        current, error = _find_deployment(name, namespace)
        if error:
            return error
        before_mem = current.get("memory_limit") or "unspecified"
        before_cpu = current.get("cpu_limit") or "unspecified"
        after_mem = args.get("memory_limit") or before_mem
        after_cpu = args.get("cpu_limit") or before_cpu
        parts = []
        if args.get("memory_limit"):
            parts.append(f"memory {before_mem} → {after_mem}")
        if args.get("cpu_limit"):
            parts.append(f"CPU {before_cpu} → {after_cpu}")
        change = ", ".join(parts) or "resource limits"
        return {
            "blocked": False,
            "summary": f"Patch {name}: {change}",
            "before": {"deployment": name, "namespace": namespace, "memory": before_mem, "cpu": before_cpu},
            "after": {"deployment": name, "namespace": namespace, "memory": after_mem, "cpu": after_cpu},
            "risk": "Medium",
        }

    if tool_name == "rollout_restart":
        name = args.get("deployment_name") or args.get("name") or ""
        current, error = _find_deployment(name, namespace)
        if error:
            return error
        return {
            "blocked": False,
            "summary": f"Rolling restart of {name}",
            "before": {
                "deployment": name,
                "namespace": namespace,
                "available_replicas": current.get("available_replicas"),
                "desired_replicas": current.get("desired_replicas"),
            },
            "after": {
                "deployment": name,
                "namespace": namespace,
                "action": "rollout restart",
                "desired_replicas": current.get("desired_replicas"),
            },
            "risk": "Low",
        }

    if tool_name == "delete_pod":
        pod_name = args.get("pod_name") or ""
        pods, error = _pods(namespace)
        if error:
            return error
        match = next((pod for pod in pods if pod.get("name") == pod_name), None)
        if not match:
            return _blocked("Pod not found", f"Pod '{pod_name}' was not found in namespace '{namespace}'.")
        return {
            "blocked": False,
            "summary": f"Delete pod {pod_name}",
            "before": {"pod": pod_name, "namespace": namespace, "status": match.get("status"), "restarts": match.get("restarts")},
            "after": {"pod": pod_name, "namespace": namespace, "status": "Terminated"},
            "risk": "High",
        }

    if tool_name == "set_deployment_env":
        name = args.get("name") or ""
        current, error = _find_deployment(name, namespace)
        if error:
            return error
        env_vars = args.get("env_vars") or {}
        keys = ", ".join(env_vars.keys()) or "environment"
        return {
            "blocked": False,
            "summary": f"Set {keys} on {name}",
            "before": {"deployment": name, "namespace": namespace, "image": current.get("image")},
            "after": {"deployment": name, "namespace": namespace, "env": env_vars},
            "risk": "Medium",
        }

    if tool_name == "set_deployment_image":
        name = args.get("name") or ""
        current, error = _find_deployment(name, namespace)
        if error:
            return error
        image = args.get("image")
        return {
            "blocked": False,
            "summary": f"Change {name} image from {current.get('image')} → {image}",
            "before": {"deployment": name, "namespace": namespace, "image": current.get("image")},
            "after": {"deployment": name, "namespace": namespace, "image": image},
            "risk": "High",
        }

    return {
        "blocked": False,
        "summary": f"Run {tool_name}",
        "before": {"namespace": namespace},
        "after": {"args": args},
        "risk": "Medium",
    }
