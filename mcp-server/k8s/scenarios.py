"""One-click demo failures and a healthy restore, simulator only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .client import get_k8s_adapter


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _pod(
    name: str,
    deployment: str,
    status: str,
    ready: bool,
    restarts: int,
    logs: str,
    events: list,
    container: str,
    exit_code: int = 0,
    exit_reason: str | None = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "deployment": deployment,
        "status": status,
        "ready": ready,
        "restarts": restarts,
        "age": "2m",
        "node": "minikube-node-01",
        "container_name": container,
        "last_exit_code": exit_code,
        "exit_reason": exit_reason,
        "logs": logs,
        "events": events,
    }


def _upsert_deployment(mock, namespace: str, name: str, **fields) -> None:
    bucket = mock.deployments.setdefault(namespace, {})
    current = bucket.get(name, {"env": {}})
    current.update(fields)
    bucket[name] = current


def _replace_pods(mock, namespace: str, deployment: str, pods: list) -> None:
    existing = mock.pods.setdefault(namespace, [])
    kept = [pod for pod in existing if pod.get("deployment") != deployment]
    mock.pods[namespace] = kept + pods


def _apply_oom(mock, namespace: str) -> None:
    _upsert_deployment(
        mock,
        namespace,
        "payment-service",
        replicas=1,
        available_replicas=0,
        image="payment-service:v2.1.0",
        memory_limit="128Mi",
        cpu_limit="250m",
        env={"DB_HOST": "postgres-prod", "PORT": "8080"},
    )
    _replace_pods(
        mock,
        namespace,
        "payment-service",
        [
            _pod(
                "payment-service-7f8d9b-xc41",
                "payment-service",
                "CrashLoopBackOff",
                False,
                9,
                (
                    f"[{_now()}] INFO  PaymentProcessor starting on port 8080\n"
                    f"[{_now()}] WARN  Heap memory threshold reached: 126MB / 128MB\n"
                    f"[{_now()}] ERROR java.lang.OutOfMemoryError: Java heap space\n"
                    f"[{_now()}] FATAL Container killed: Exit Code 137 (OOMKilled)"
                ),
                [
                    {
                        "type": "Warning",
                        "reason": "OOMKilled",
                        "message": "Memory limit 128Mi exceeded. Process terminated with exit code 137.",
                        "count": 9,
                        "last_seen": "20s ago",
                    },
                    {
                        "type": "Warning",
                        "reason": "BackOff",
                        "message": "Back-off restarting failed container payment-container",
                        "count": 16,
                        "last_seen": "10s ago",
                    },
                ],
                "payment-container",
                137,
                "OOMKilled",
            )
        ],
    )


def _apply_crashloop(mock, namespace: str) -> None:
    _upsert_deployment(
        mock,
        namespace,
        "order-service",
        replicas=1,
        available_replicas=0,
        image="order-service:v1.8.0",
        memory_limit="256Mi",
        cpu_limit="200m",
        env={"PORT": "8080"},
    )
    _replace_pods(
        mock,
        namespace,
        "order-service",
        [
            _pod(
                "order-service-6c1aa2-kk19",
                "order-service",
                "CrashLoopBackOff",
                False,
                6,
                (
                    f"[{_now()}] INFO  order-service boot\n"
                    f"[{_now()}] ERROR Redis connection failed: missing REDIS_HOST\n"
                    f"[{_now()}] FATAL Unable to connect to redis-master:6379. Exiting."
                ),
                [
                    {
                        "type": "Warning",
                        "reason": "BackOff",
                        "message": "Back-off restarting failed container order-container. Missing REDIS_HOST.",
                        "count": 6,
                        "last_seen": "15s ago",
                    }
                ],
                "order-container",
                1,
                "Error",
            )
        ],
    )


def _healthy_pod(name: str, deployment: str, container: str, log: str) -> Dict[str, Any]:
    return _pod(
        name,
        deployment,
        "Running",
        True,
        0,
        f"[{_now()}] INFO {log}",
        [{"type": "Normal", "reason": "Started", "message": log, "count": 1, "last_seen": "just now"}],
        container,
    )


def _restore(mock, namespace: str) -> None:
    specs = [
        ("payment-service", 2, "payment-service:v2.1.0", "512Mi", "500m", {"DB_HOST": "postgres-prod", "PORT": "8080"}, "payment-container", "Payment processor healthy. Heap 180MB / 512MB."),
        ("user-auth-service", 2, "auth-service:v1.4.0", "512Mi", "500m", {"REDIS_HOST": "redis-prod"}, "auth-container", "Auth server healthy."),
        ("frontend-web", 3, "frontend-app:v3.0.1", "256Mi", "200m", {"API_URL": "https://api.internal"}, "web-container", "HTTP server listening on 0.0.0.0:80."),
        ("order-service", 2, "order-service:v1.8.0", "256Mi", "200m", {"REDIS_HOST": "redis-prod.production.svc.cluster.local"}, "order-container", "Connected to Redis. Accepting orders."),
        ("notification-service", 1, "nginx:alpine", "128Mi", "100m", {}, "notify-container", "Notification worker ready. Image nginx:alpine."),
        ("inventory-service", 1, "inventory-service:v1.2.0", "512Mi", "300m", {"DB_CONNECTION_STRING": "postgresql://infragpt:infragpt_secret@postgres-prod:5432/inventory"}, "inventory-container", "Inventory connected to PostgreSQL."),
    ]
    for name, replicas, image, memory, cpu, env, container, log in specs:
        _upsert_deployment(
            mock,
            namespace,
            name,
            replicas=replicas,
            available_replicas=replicas,
            image=image,
            memory_limit=memory,
            cpu_limit=cpu,
            env=env,
        )
        pods = [
            _healthy_pod(f"{name}-{index + 1:02d}ab-ok{index}", name, container, log)
            for index in range(replicas)
        ]
        _replace_pods(mock, namespace, name, pods)


def apply_demo_scenario_impl(scenario: str, namespace: str = "production") -> Dict[str, Any]:
    adapter = get_k8s_adapter()
    if adapter.is_live:
        return {
            "success": False,
            "error": "Demo scenarios are disabled on live clusters",
            "message": "OOM and CrashLoop actions only change the built-in simulator. The live cluster was not modified.",
        }

    name = (scenario or "").strip().lower().replace("-", "_")
    ns = namespace or "production"
    mock = adapter.mock
    mock.deployments.setdefault(ns, {})
    mock.pods.setdefault(ns, [])

    if name in {"oom", "trigger_oom"}:
        _apply_oom(mock, ns)
        return {
            "success": True,
            "scenario": "oom",
            "namespace": ns,
            "message": "payment-service is now OOMKilled with a 128Mi memory limit.",
        }
    if name in {"crashloop", "trigger_crashloop"}:
        _apply_crashloop(mock, ns)
        return {
            "success": True,
            "scenario": "crashloop",
            "namespace": ns,
            "message": "order-service is now CrashLoopBackOff because REDIS_HOST is missing.",
        }
    if name in {"restore", "healthy", "restore_healthy"}:
        _restore(mock, ns)
        return {
            "success": True,
            "scenario": "restore",
            "namespace": ns,
            "message": f"Workloads in {ns} were restored to a healthy state.",
        }
    return {
        "success": False,
        "error": "The operation could not be completed",
        "message": "Unknown scenario. Use oom, crashloop, or restore.",
    }
