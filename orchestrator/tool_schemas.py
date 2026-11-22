"""Gemini function declarations for the Kubernetes MCP tools."""

from __future__ import annotations

from google.genai import types


def _decl(name: str, description: str, properties: dict, required: list[str] | None = None):
    return types.FunctionDeclaration(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    )


def gemini_tools() -> list:
    declarations = [
        _decl(
            "list_pods",
            "List pods in a namespace with status, readiness, and restart count.",
            {"namespace": {"type": "string", "description": "Kubernetes namespace"}},
        ),
        _decl(
            "get_pod_logs",
            "Read recent logs from a pod.",
            {
                "pod_name": {"type": "string", "description": "Pod name or prefix"},
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
                "tail_lines": {"type": "integer", "description": "How many lines to return"},
            },
            ["pod_name"],
        ),
        _decl(
            "get_pod_events",
            "Read Kubernetes events for a pod, including OOMKilled and BackOff.",
            {
                "pod_name": {"type": "string", "description": "Pod name"},
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
            },
            ["pod_name"],
        ),
        _decl(
            "describe_resource",
            "Describe a pod or deployment.",
            {
                "resource_type": {"type": "string", "description": "pod or deployment"},
                "name": {"type": "string", "description": "Resource name"},
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
            },
            ["resource_type", "name"],
        ),
        _decl(
            "list_deployments",
            "List deployments with replica counts and resource limits.",
            {"namespace": {"type": "string", "description": "Kubernetes namespace"}},
        ),
        _decl(
            "get_cluster_nodes",
            "List cluster nodes and their CPU and memory capacity.",
            {},
        ),
        _decl(
            "get_cluster_status",
            "Report whether the cluster connection is live or simulated, plus namespaces.",
            {},
        ),
        _decl(
            "scale_deployment",
            "Scale a deployment. This mutates the cluster and must pass the approval gate.",
            {
                "name": {"type": "string", "description": "Deployment name"},
                "replicas": {"type": "integer", "description": "Target replica count"},
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
            },
            ["name", "replicas"],
        ),
        _decl(
            "patch_deployment_resources",
            "Change CPU or memory limits. This mutates the cluster and must pass the approval gate.",
            {
                "name": {"type": "string", "description": "Deployment name"},
                "memory_limit": {"type": "string", "description": "Memory limit such as 512Mi"},
                "cpu_limit": {"type": "string", "description": "CPU limit such as 500m"},
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
            },
            ["name"],
        ),
        _decl(
            "set_deployment_env",
            "Set environment variables on a deployment. This mutates the cluster and must pass the approval gate.",
            {
                "name": {"type": "string", "description": "Deployment name"},
                "env_vars": {
                    "type": "object",
                    "description": "Environment variables to set",
                },
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
            },
            ["name", "env_vars"],
        ),
        _decl(
            "set_deployment_image",
            "Change a deployment container image. This mutates the cluster and must pass the approval gate.",
            {
                "name": {"type": "string", "description": "Deployment name"},
                "image": {"type": "string", "description": "Image tag"},
                "container_name": {"type": "string", "description": "Container name"},
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
            },
            ["name", "image"],
        ),
        _decl(
            "rollout_restart",
            "Rolling restart a deployment. This mutates the cluster and must pass the approval gate.",
            {
                "deployment_name": {"type": "string", "description": "Deployment name"},
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
            },
            ["deployment_name"],
        ),
        _decl(
            "delete_pod",
            "Delete a pod. This mutates the cluster and must pass the approval gate.",
            {
                "pod_name": {"type": "string", "description": "Exact pod name"},
                "namespace": {"type": "string", "description": "Kubernetes namespace"},
            },
            ["pod_name"],
        ),
    ]
    return [types.Tool(function_declarations=declarations)]
