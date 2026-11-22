"""
Kubernetes Client and Operations Module for InfraGPT
"""

from .client import get_k8s_adapter, K8sAdapter
from .read_tools import (
    list_pods_impl,
    get_pod_logs_impl,
    get_pod_events_impl,
    describe_resource_impl,
    list_deployments_impl,
    get_cluster_nodes_impl
)
from .write_tools import (
    scale_deployment_impl,
    patch_deployment_resources_impl,
    rollout_restart_impl,
    delete_pod_impl
)

__all__ = [
    "get_k8s_adapter",
    "K8sAdapter",
    "list_pods_impl",
    "get_pod_logs_impl",
    "get_pod_events_impl",
    "describe_resource_impl",
    "list_deployments_impl",
    "get_cluster_nodes_impl",
    "scale_deployment_impl",
    "patch_deployment_resources_impl",
    "rollout_restart_impl",
    "delete_pod_impl"
]
