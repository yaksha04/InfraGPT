"""
Pydantic Data Models & Typed Schemas for InfraGPT
Defines strong typing for API request payloads, cluster topology streams, and audit logs.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class PodStatusSchema(BaseModel):
    name: str = Field(..., description="Kubernetes Pod name")
    namespace: str = Field("default", description="Target namespace")
    status: str = Field(..., description="Current pod phase (Running, CrashLoopBackOff, Error)")
    ready: bool = Field(..., description="Readiness probe status")
    restarts: int = Field(0, description="Container restart count")
    age: str = Field(..., description="Pod creation timestamp / duration")
    node: str = Field("unassigned", description="Node host running the pod")
    is_healthy: bool = Field(True, description="Evaluated health boolean")


class DeploymentStatusSchema(BaseModel):
    name: str
    namespace: str
    replicas: int
    available_replicas: int
    image: str
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None


class AuditLogEventSchema(BaseModel):
    id: str
    timestamp: str
    action: str
    target: str
    user: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ClusterOverviewResponse(BaseModel):
    mode: str = Field("live", description="'live' or 'mock'")
    cluster: str
    namespaces: List[str]
    node_count: int
    ai_engine: str
