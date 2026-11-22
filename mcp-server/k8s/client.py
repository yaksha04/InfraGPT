"""
Kubernetes Client Adapter for InfraGPT
Handles connection to live Kubernetes clusters and provides an in-memory mock fallback for offline development/testing.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    client = None
    config = None
    ApiException = Exception

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("infragpt-k8s")


class MockK8sCluster:
    """In-memory mock Kubernetes cluster for offline testing and initial demonstration."""

    def __init__(self):
        self.nodes = [
            {
                "name": "minikube-node-01",
                "status": "Ready",
                "roles": ["control-plane", "master"],
                "kubelet_version": "v1.28.3",
                "cpu_capacity": "4",
                "memory_capacity": "8192Mi"
            }
        ]

        self.deployments = {
            "production": {
                "payment-service": {
                    "replicas": 1,
                    "available_replicas": 0,
                    "image": "payment-service:v2.1.0",
                    "memory_limit": "256Mi",
                    "cpu_limit": "250m",
                    "env": {"DB_HOST": "postgres-prod", "PORT": "8080"}
                },
                "user-auth-service": {
                    "replicas": 2,
                    "available_replicas": 2,
                    "image": "auth-service:v1.4.0",
                    "memory_limit": "512Mi",
                    "cpu_limit": "500m",
                    "env": {"REDIS_HOST": "redis-prod"}
                },
                "frontend-web": {
                    "replicas": 3,
                    "available_replicas": 3,
                    "image": "frontend-app:v3.0.1",
                    "memory_limit": "256Mi",
                    "cpu_limit": "200m",
                    "env": {"API_URL": "https://api.internal"}
                },
                "order-service": {
                    "replicas": 1,
                    "available_replicas": 0,
                    "image": "order-service:v1.8.0",
                    "memory_limit": "256Mi",
                    "cpu_limit": "200m",
                    "env": {"PORT": "8080"}
                },
                "notification-service": {
                    "replicas": 1,
                    "available_replicas": 0,
                    "image": "nginx:v999-broken-tag",
                    "memory_limit": "128Mi",
                    "cpu_limit": "100m",
                    "env": {}
                },
                "inventory-service": {
                    "replicas": 1,
                    "available_replicas": 0,
                    "image": "inventory-service:v1.2.0",
                    "memory_limit": "256Mi",
                    "cpu_limit": "200m",
                    "env": {}
                }
            },
            "staging": {
                "preview-api": {
                    "replicas": 1,
                    "available_replicas": 1,
                    "image": "preview-api:v0.9.0",
                    "memory_limit": "256Mi",
                    "cpu_limit": "200m",
                    "env": {"ENV": "staging"}
                }
            },
            "default": {
                "nginx-ingress": {
                    "replicas": 1,
                    "available_replicas": 1,
                    "image": "nginx:latest",
                    "memory_limit": "128Mi",
                    "cpu_limit": "100m",
                    "env": {}
                }
            }
        }

        self.pods = {
            "production": [
                {
                    "name": "payment-service-7f8d9b-xc41",
                    "deployment": "payment-service",
                    "status": "CrashLoopBackOff",
                    "ready": False,
                    "restarts": 7,
                    "age": "42m",
                    "node": "minikube-node-01",
                    "container_name": "payment-container",
                    "last_exit_code": 137,
                    "exit_reason": "OOMKilled",
                    "logs": (
                        "[2026-08-14 14:40:01] INFO  PaymentProcessor starting up on port 8080...\n"
                        "[2026-08-14 14:40:03] INFO  Connected to PostgreSQL pool (max=50)\n"
                        "[2026-08-14 14:40:10] WARN  Heap memory threshold reached: 245MB / 256MB\n"
                        "[2026-08-14 14:40:12] ERROR java.lang.OutOfMemoryError: Java heap space\n"
                        "[2026-08-14 14:40:12] FATAL Container runtime killed process: Exit Code 137 (OOMKilled)"
                    ),
                    "events": [
                        {"type": "Warning", "reason": "OOMKilled", "message": "Memory limit 256Mi exceeded. Process terminated with exit code 137.", "count": 7, "last_seen": "2m ago"},
                        {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container payment-container in pod payment-service-7f8d9b-xc41", "count": 14, "last_seen": "30s ago"}
                    ]
                },
                {
                    "name": "user-auth-service-54a8bc-19qa",
                    "deployment": "user-auth-service",
                    "status": "Running",
                    "ready": True,
                    "restarts": 0,
                    "age": "4h",
                    "node": "minikube-node-01",
                    "container_name": "auth-container",
                    "last_exit_code": 0,
                    "exit_reason": None,
                    "logs": "[2026-08-14 15:00:00] INFO Auth server running healthy. 0 errors in last 1000 requests.",
                    "events": [
                        {"type": "Normal", "reason": "Started", "message": "Container auth-container started successfully", "count": 1, "last_seen": "4h ago"}
                    ]
                },
                {
                    "name": "user-auth-service-54a8bc-88zx",
                    "deployment": "user-auth-service",
                    "status": "Running",
                    "ready": True,
                    "restarts": 0,
                    "age": "4h",
                    "node": "minikube-node-01",
                    "container_name": "auth-container",
                    "last_exit_code": 0,
                    "exit_reason": None,
                    "logs": "[2026-08-14 15:00:00] INFO Auth replica healthy.",
                    "events": []
                },
                {
                    "name": "frontend-web-99df71-k81a",
                    "deployment": "frontend-web",
                    "status": "Running",
                    "ready": True,
                    "restarts": 0,
                    "age": "6h",
                    "node": "minikube-node-01",
                    "container_name": "web-container",
                    "last_exit_code": 0,
                    "exit_reason": None,
                    "logs": "HTTP Server listening on 0.0.0.0:80",
                    "events": []
                },
                {
                    "name": "frontend-web-99df71-k82b",
                    "deployment": "frontend-web",
                    "status": "Running",
                    "ready": True,
                    "restarts": 0,
                    "age": "6h",
                    "node": "minikube-node-01",
                    "container_name": "web-container",
                    "last_exit_code": 0,
                    "exit_reason": None,
                    "logs": "HTTP Server listening on 0.0.0.0:80",
                    "events": []
                },
                {
                    "name": "frontend-web-99df71-k83c",
                    "deployment": "frontend-web",
                    "status": "Running",
                    "ready": True,
                    "restarts": 1,
                    "age": "5h",
                    "node": "minikube-node-01",
                    "container_name": "web-container",
                    "last_exit_code": 0,
                    "exit_reason": None,
                    "logs": "HTTP Server listening on 0.0.0.0:80",
                    "events": []
                },
                {
                    "name": "order-service-6c1aa2-kk19",
                    "deployment": "order-service",
                    "status": "CrashLoopBackOff",
                    "ready": False,
                    "restarts": 6,
                    "age": "25m",
                    "node": "minikube-node-01",
                    "container_name": "order-container",
                    "last_exit_code": 1,
                    "exit_reason": "Error",
                    "logs": (
                        "[2026-08-14 15:10:01] INFO  order-service boot\n"
                        "[2026-08-14 15:10:02] ERROR Redis connection failed: missing REDIS_HOST\n"
                        "[2026-08-14 15:10:02] FATAL Unable to connect to redis-master:6379. Exiting."
                    ),
                    "events": [
                        {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container. Missing REDIS_HOST.", "count": 6, "last_seen": "40s ago"}
                    ]
                },
                {
                    "name": "notification-service-2ab91c-qq7",
                    "deployment": "notification-service",
                    "status": "ImagePullBackOff",
                    "ready": False,
                    "restarts": 4,
                    "age": "18m",
                    "node": "minikube-node-01",
                    "container_name": "notify-container",
                    "last_exit_code": 1,
                    "exit_reason": "ImagePullBackOff",
                    "logs": "Failed to pull image nginx:v999-broken-tag: manifest unknown",
                    "events": [
                        {"type": "Warning", "reason": "Failed", "message": "Failed to pull image nginx:v999-broken-tag: manifest unknown", "count": 4, "last_seen": "1m ago"},
                        {"type": "Warning", "reason": "ImagePullBackOff", "message": "Back-off pulling image nginx:v999-broken-tag", "count": 4, "last_seen": "30s ago"}
                    ]
                },
                {
                    "name": "inventory-service-88cd10-pl2",
                    "deployment": "inventory-service",
                    "status": "CrashLoopBackOff",
                    "ready": False,
                    "restarts": 5,
                    "age": "33m",
                    "node": "minikube-node-01",
                    "container_name": "inventory-container",
                    "last_exit_code": 1,
                    "exit_reason": "Error",
                    "logs": (
                        "[2026-08-14 15:12:00] INFO  inventory-service boot\n"
                        "[2026-08-14 15:12:01] ERROR Missing mandatory environment variable DB_CONNECTION_STRING\n"
                        "[2026-08-14 15:12:01] FATAL Refusing to start without a database."
                    ),
                    "events": [
                        {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container. DB_CONNECTION_STRING is unset.", "count": 5, "last_seen": "25s ago"}
                    ]
                }
            ],
            "staging": [
                {
                    "name": "preview-api-12ab34-st1",
                    "deployment": "preview-api",
                    "status": "Running",
                    "ready": True,
                    "restarts": 0,
                    "age": "2h",
                    "node": "minikube-node-01",
                    "container_name": "preview",
                    "last_exit_code": 0,
                    "exit_reason": None,
                    "logs": "preview-api healthy in staging",
                    "events": []
                }
            ],
            "default": [
                {
                    "name": "nginx-ingress-11aa22-pl99",
                    "deployment": "nginx-ingress",
                    "status": "Running",
                    "ready": True,
                    "restarts": 0,
                    "age": "1d",
                    "node": "minikube-node-01",
                    "container_name": "nginx",
                    "last_exit_code": 0,
                    "exit_reason": None,
                    "logs": "nginx/1.25.1 ready for requests",
                    "events": []
                }
            ]
        }


class K8sAdapter:
    """Provides a unified API over live Kubernetes clusters with automatic fallback to MockK8sCluster."""

    def __init__(self):
        self.is_live = False
        self.mock = MockK8sCluster()
        self._init_connection()

    def _init_connection(self):
        mode = os.getenv("INFRAGPT_K8S_MODE", "mock").strip().lower()
        if mode not in {"live", "cluster"}:
            logger.info("Simulator mode. Set INFRAGPT_K8S_MODE=live to use the kubeconfig.")
            self.is_live = False
            return

        if not KUBERNETES_AVAILABLE:
            logger.warning("Kubernetes Python SDK not installed. Running in Mock Mode.")
            self.is_live = False
            return

        try:
            # Check if running in-cluster
            if os.getenv("K8S_IN_CLUSTER", "false").lower() == "true":
                config.load_incluster_config()
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                self.is_live = True
                logger.info("Connected to live Kubernetes cluster via in-cluster config.")
            else:
                raw_path = os.getenv("KUBECONFIG_PATH", "~/.kube/config")
                kubeconfig_path = os.path.expanduser(raw_path)
                if os.path.exists(kubeconfig_path):
                    config.load_kube_config(config_file=kubeconfig_path)
                    self.v1 = client.CoreV1Api()
                    self.apps_v1 = client.AppsV1Api()
                    # Perform a fast test call
                    self.v1.list_namespace(_request_timeout=3)
                    self.is_live = True
                    logger.info(f"Connected to live Kubernetes cluster via {kubeconfig_path}")
                else:
                    raise FileNotFoundError(f"Kubeconfig not found at {kubeconfig_path}")
        except Exception as e:
            logger.warning(f"Could not connect to live Kubernetes cluster ({e}). Activating Mock Mode for InfraGPT development.")
            self.is_live = False

    def get_status(self) -> Dict[str, Any]:
        if not self.is_live:
            self._init_connection()
        return {
            "mode": "live" if self.is_live else "mock",
            "cluster": "Live Kubernetes Cluster" if self.is_live else "InfraGPT Simulated Minikube Cluster",
            "namespaces": sorted(self.mock.pods.keys()) if not self.is_live else [ns.metadata.name for ns in self.v1.list_namespace().items]
        }


_adapter_instance = None


def get_k8s_adapter() -> K8sAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = K8sAdapter()
    return _adapter_instance
