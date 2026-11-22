# 🌐 InfraGPT
## Natural Language Kubernetes Manager via MCP Server

> **Category:** MCP Server + AI + DevOps (Kubernetes)  
> **Difficulty:** ⭐⭐⭐⭐⭐ (5/5)  
> **Impressiveness:** 🔥🔥🔥🔥🔥 (5/5)  
> **Suitable For:** 7th Semester Minor Project (4 Credits)  
> **Type:** Open Source (MIT License)

---

## 🧩 Problem Statement

Kubernetes (K8s) is the most widely used container orchestration platform in the world — but it has a **steep learning curve**. Engineers must memorize dozens of `kubectl` commands, YAML syntax, and cluster architecture. This leads to:

- New developers unable to interact with production clusters
- Slow incident response (wrong kubectl command = wrong info)
- Expertise bottleneck — only senior SREs can manage clusters confidently

**No open-source tool currently allows non-experts to manage K8s clusters using plain English via an MCP-compliant AI agent.**

---

## 💡 What You'll Build

An MCP Server that gives any AI agent **safe, scoped, natural language access to a Kubernetes cluster**. Just type what you want in English:

```
👤 User: "Show me all pods in the production namespace and 
         tell me which ones are not healthy"

🤖 AI  → calls MCP tool: list_pods(namespace="production")
       → calls MCP tool: get_pod_events(pod="payment-xyz")
       → calls MCP tool: get_pod_logs(pod="payment-xyz", tail=50)
       → Responds: "3 pods are healthy. payment-service-xyz is in 
                   CrashLoopBackOff. Root cause: OOMKilled (memory 
                   limit 256Mi exceeded). Recommend increasing 
                   memory limit to 512Mi."

👤 User: "Increase the memory limit for payment-service"

🤖 AI  → [APPROVAL REQUIRED] "I will patch payment-service 
         deployment memory limit from 256Mi to 512Mi. Confirm? (y/n)"

👤 User: "yes"

🤖 AI  → calls MCP tool: patch_deployment(name="payment-service", 
                          memory_limit="512Mi")
       → "Done! payment-service redeployed. New pods are starting..."
```

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      INFRAGPT ARCHITECTURE                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   MCP HOST (React Chat UI)                  │ │
│  │   User types natural language → Sent to Orchestrator Agent  │ │
│  └────────────────────────────┬────────────────────────────────┘ │
│                               │                                  │
│  ┌────────────────────────────▼────────────────────────────────┐ │
│  │               AI Orchestrator (Python Agent)                │ │
│  │   Gemini / Ollama → understands intent → calls MCP tools   │ │
│  │   Implements: Human-in-the-Loop for write operations        │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │  MCP Protocol (JSON-RPC 2.0)        │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │              YOUR CUSTOM MCP SERVER (Core)                  │ │
│  │                                                             │ │
│  │  READ TOOLS              │  WRITE TOOLS (approval needed)  │ │
│  │  ─────────────────────── │  ───────────────────────────── │ │
│  │  list_pods               │  scale_deployment               │ │
│  │  get_pod_logs            │  patch_deployment               │ │
│  │  describe_resource       │  delete_pod                     │ │
│  │  get_events              │  apply_manifest                 │ │
│  │  get_metrics             │  rollout_restart                │ │
│  │  list_services           │  create_configmap               │ │
│  │  get_namespaces          │  (ALL need human confirm)       │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │  kubernetes Python client          │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │            KUBERNETES CLUSTER (Minikube / Kind)             │ │
│  │                                                             │ │
│  │   [Namespace: default]    [Namespace: production]           │ │
│  │   nginx-pod, redis-pod    payment-svc, user-svc, db-pod     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Audit + Metrics         [PostgreSQL]  [Prometheus sidecar] │ │
│  │  Every action logged     Incident DB   Resource metrics     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack (Complete)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **MCP Server** | Python + `fastmcp` | Core MCP server implementation |
| **K8s Client** | `kubernetes` Python client | Talk to the cluster |
| **AI Brain** | Gemini 1.5 Flash OR Ollama + Llama3 | Natural language understanding |
| **Orchestrator** | Python agent with LangGraph (optional) | Manages conversation + tool calls |
| **Frontend Chat UI** | React + Tailwind (or Next.js) | Terminal-style chat interface |
| **Database** | PostgreSQL | Audit logs of every AI action |
| **Local K8s** | Minikube or Kind | Local cluster for demo |
| **Containerization** | Docker + Docker Compose | One-command setup |
| **CI/CD** | GitHub Actions | Auto-test the MCP server tools |
| **Monitoring** | Prometheus + Grafana | Show cluster health in dashboard |
| **RBAC** | Kubernetes ServiceAccount + ClusterRole | Scope the agent's permissions |

---

## 🔧 MCP Server Tools (Full Implementation)

### READ Tools (No Approval Needed)

```python
from fastmcp import FastMCP
from kubernetes import client, config

mcp = FastMCP("InfraGPT-K8s-Server")
config.load_kube_config()  # or load_incluster_config() when running in-cluster

# ── READ TOOLS ──────────────────────────────────────────────────

@mcp.tool()
def list_pods(namespace: str = "default") -> dict:
    """List all pods in a namespace with their status"""
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace=namespace)
    return [
        {
            "name": p.metadata.name,
            "status": p.status.phase,
            "ready": all(c.ready for c in (p.status.container_statuses or [])),
            "restarts": sum(c.restart_count for c in (p.status.container_statuses or []))
        }
        for p in pods.items
    ]

@mcp.tool()
def get_pod_logs(pod_name: str, namespace: str = "default", tail: int = 100) -> str:
    """Get the last N lines of logs from a pod"""
    v1 = client.CoreV1Api()
    return v1.read_namespaced_pod_log(
        name=pod_name, namespace=namespace, tail_lines=tail
    )

@mcp.tool()
def describe_resource(resource_type: str, name: str, namespace: str = "default") -> dict:
    """Describe a K8s resource (pod, deployment, service, etc.)"""
    ...

@mcp.tool()
def get_pod_events(pod_name: str, namespace: str = "default") -> list:
    """Get events for a specific pod (useful for diagnosing issues)"""
    ...

@mcp.tool()
def list_deployments(namespace: str = "default") -> list:
    """List all deployments with replica status"""
    ...

@mcp.tool()
def get_cluster_nodes() -> list:
    """Get all nodes, their status, and resource capacity"""
    ...

@mcp.tool()
def get_namespaces() -> list:
    """List all namespaces in the cluster"""
    ...

@mcp.tool()
def get_resource_usage(namespace: str = "default") -> dict:
    """Get CPU and memory usage for pods (requires metrics-server)"""
    ...

# ── WRITE TOOLS (require human approval in orchestrator) ─────────

@mcp.tool()
def scale_deployment(name: str, replicas: int, namespace: str = "default") -> str:
    """⚠️ WRITE: Scale a deployment to N replicas"""
    ...

@mcp.tool()
def delete_pod(pod_name: str, namespace: str = "default") -> str:
    """⚠️ WRITE: Force delete a pod (it will be recreated)"""
    ...

@mcp.tool()
def rollout_restart(deployment_name: str, namespace: str = "default") -> str:
    """⚠️ WRITE: Rolling restart a deployment"""
    ...

@mcp.tool()
def patch_deployment(name: str, namespace: str, patch: dict) -> str:
    """⚠️ WRITE: Apply a patch to a deployment spec"""
    ...
```

---

## 🗂️ Project Folder Structure

```
infragpt/
├── README.md
├── LICENSE                     # MIT
├── docker-compose.yml          # Full stack
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── test-mcp-server.yml
│
├── mcp-server/                 # 🔑 CORE: Your K8s MCP Server
│   ├── server.py               # Main fastmcp server
│   ├── tools/
│   │   ├── read_tools.py       # list_pods, get_logs, describe...
│   │   ├── write_tools.py      # scale, delete, patch...
│   │   └── metrics_tools.py    # CPU/memory queries
│   ├── k8s_client.py           # Kubernetes client setup
│   ├── requirements.txt
│   └── Dockerfile
│
├── orchestrator/               # AI Agent Brain
│   ├── agent.py                # Main agent with approval logic
│   ├── mcp_client.py           # Connects to MCP server
│   ├── hitl.py                 # Human-in-the-Loop handler
│   ├── prompt.py               # System prompts
│   └── requirements.txt
│
├── chat-ui/                    # React Chat Interface
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatBox.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── ApprovalModal.tsx   # ← Human approval dialog
│   │   │   └── ClusterStatus.tsx
│   │   └── api/
│   │       └── chat.ts
│   └── package.json
│
├── infra/
│   ├── k8s/
│   │   ├── serviceaccount.yaml     # RBAC for the agent
│   │   ├── clusterrole.yaml        # Scoped permissions
│   │   └── demo-apps/             # Sample apps to manage
│   │       ├── nginx.yaml
│   │       ├── redis.yaml
│   │       └── broken-app.yaml    # App that intentionally crashes
│   └── monitoring/
│       ├── prometheus.yaml
│       └── grafana-dashboard.json
│
└── audit-db/
    ├── schema.sql
    └── Dockerfile
```

---

## 🔐 Security: RBAC Configuration

This is a **critical and impressive feature**. You'll create scoped Kubernetes permissions so the AI agent can't do everything:

```yaml
# clusterrole.yaml — Scope what the agent CAN do
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: infragpt-agent-role
rules:
  # READ permissions (always allowed)
  - apiGroups: [""]
    resources: ["pods", "services", "namespaces", "events", "nodes"]
    verbs: ["get", "list", "watch"]
  
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]

  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch"]

  # WRITE permissions (require human approval at app level)
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["patch", "update"]

  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["delete"]
```

---

## 🧠 Human-in-the-Loop System

The crown jewel feature:

```python
# hitl.py — Human approval before any write operation

class ApprovalGate:
    WRITE_TOOLS = [
        "scale_deployment",
        "delete_pod",
        "rollout_restart",
        "patch_deployment",
        "apply_manifest"
    ]
    
    def requires_approval(self, tool_name: str) -> bool:
        return tool_name in self.WRITE_TOOLS
    
    def format_approval_request(self, tool_name: str, args: dict) -> str:
        """Formats a human-readable approval message"""
        messages = {
            "scale_deployment": f"⚠️ Scale '{args['name']}' to {args['replicas']} replicas in '{args['namespace']}'?",
            "delete_pod": f"⚠️ Delete pod '{args['pod_name']}' in '{args['namespace']}'?",
            "rollout_restart": f"⚠️ Rolling restart '{args['deployment_name']}' in '{args['namespace']}'?"
        }
        return messages.get(tool_name, f"Execute {tool_name} with {args}?")
```

---

## 📊 Chat UI Features

| Feature | Description |
|---------|-------------|
| Terminal-style chat | Dark themed, monospace font |
| Real-time cluster status sidebar | Shows node health, pod counts |
| ✅ Approval modals | Pop-up for every write operation |
| Action audit trail | Side panel with all AI actions |
| Multi-namespace selector | Switch context in UI |
| Tool call visualization | Show which MCP tools were called |
| Response streaming | AI typing effect for responses |

---

## 💬 Example Conversations

```
User: "What's wrong with the production namespace?"

AI: Checking production namespace...
    - Running get_events for all pods
    - Found: payment-svc-789 is CrashLoopBackOff (5 restarts)
    - Found: worker-pod-456 is OOMKilled
    
    📊 Summary:
    • payment-service: CrashLoopBackOff — exit code 137 (OOM)
    • worker-pod: Killed — memory limit 128Mi exceeded
    
    Recommended actions:
    1. Increase memory limits for both services
    2. Check application for memory leaks

User: "Scale up payment-service to 3 replicas"

AI: [APPROVAL REQUIRED]
    ⚠️ I'll scale payment-service from 1 → 3 replicas in production.
    This will consume additional cluster resources.
    Type 'confirm' to proceed or 'cancel' to abort.

User: "confirm"

AI: ✅ Scaled payment-service to 3 replicas.
    Pods are starting: payment-svc-new-1, payment-svc-new-2
    ETA: ~45 seconds for all pods to be Ready.
```

---

## 🚦 Development Phases

### Phase 1 — K8s + MCP Server (Week 1-2)
- [ ] Set up Minikube locally
- [ ] Implement all READ tools in the MCP server
- [ ] Test with `fastmcp` CLI directly
- [ ] RBAC setup (ServiceAccount, ClusterRole)

### Phase 2 — AI Orchestrator (Week 3-4)
- [ ] Connect Gemini/Ollama to the MCP server
- [ ] Implement HITL approval system
- [ ] Write system prompts for K8s operations
- [ ] Test end-to-end: chat → tool call → K8s action

### Phase 3 — Write Tools + Safety (Week 5)
- [ ] Implement WRITE tools (scale, delete, restart)
- [ ] Enforce approval gate for all writes
- [ ] Audit log to PostgreSQL

### Phase 4 — Chat UI + Demo (Week 6-8)
- [ ] React chat UI with approval modals
- [ ] Deploy sample broken apps (demo scenarios)
- [ ] Docker Compose full stack
- [ ] Record demo video for submission

---

## 🌟 Unique Innovations

1. **Permission-scoped MCP** — read vs write tool separation at both MCP and RBAC level
2. **HITL approval UI** — every destructive action gets a modal
3. **Crash loop diagnosis** — AI automatically pulls events + logs + suggests fix
4. **Meta deployment** — InfraGPT itself is deployed AS a K8s pod (it manages the cluster it lives in)
5. **Multi-namespace support** — switch between namespaces in the chat

---

## 🎓 What You'll Learn

- Kubernetes architecture (pods, deployments, services, RBAC)
- `kubectl` internals via the Python kubernetes client
- MCP Server development with `fastmcp`
- Human-in-the-Loop AI systems
- LLM prompt engineering for structured operations
- React + real-time chat UIs
- Docker + K8s deployment
- Security best practices (RBAC, principle of least privilege)

---

## 📦 How to Run (for evaluators)

```bash
# 1. Start Minikube
minikube start

# 2. Deploy demo apps
kubectl apply -f infra/k8s/demo-apps/

# 3. Clone + run InfraGPT
git clone https://github.com/YOUR_USERNAME/infragpt
cp .env.example .env  # Add GEMINI_API_KEY

docker-compose up -d

# 4. Open chat UI
http://localhost:3000

# Try: "Show me all pods" or "What's broken?"
```

---

## 🔗 References

- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [FastMCP Library](https://github.com/jlowin/fastmcp)
- [MCP Protocol Docs](https://modelcontextprotocol.io)
- [Minikube (local K8s)](https://minikube.sigs.k8s.io/)
- [Kind (K8s in Docker)](https://kind.sigs.k8s.io/)
- [Gemini API (Free Tier)](https://ai.google.dev/)

---

*Document prepared for 7th Semester Minor Project (4 Credits) | August 2026*
