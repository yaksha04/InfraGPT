# InfraGPT Viva Defense & Examiner Q&A Guide

---

### Key Questions & Model Technical Answers for Major Project Defense

#### Q1: What is InfraGPT and what core problem does it solve?
> **Answer:** Modern Kubernetes clusters generate high volumes of telemetry, events, and logs during outages. Diagnosing issues like `OOMKilled` or `CrashLoopBackOff` manually requires running multiple `kubectl` commands (`kubectl describe`, `kubectl logs`, `kubectl get events`), leading to prolonged Mean Time to Resolution (MTTR). InfraGPT is an autonomous AI Site Reliability Engineer that correlates cluster events using the Model Context Protocol (MCP), diagnoses the root cause in natural language, and executes secure remediations via a Human-In-The-Loop (HITL) gate.

#### Q2: Why did you choose Model Context Protocol (MCP) instead of standard REST or LangChain?
> **Answer:** Model Context Protocol (Anthropic open standard) provides standardized, decoupled tool discovery and schema negotiation. Unlike tightly coupled LangChain abstractions, FastMCP servers cleanly separate LLM reasoning from the cluster interface, making tools reusable across CLI, Web, and IDE agents.

#### Q3: How do you prevent the LLM from hallucinating destructive actions (e.g. deleting production namespaces)?
> **Answer:** We implement defense-in-depth through three layers:
> 1. **Zero-Latency HITL Security Interception:** Every write operation is halted before reaching the cluster and requires human authorization via a unique UUIDv4 token.
> 2. **Kubernetes Least-Privilege RBAC:** The agent's `ClusterRole` lacks namespace deletion, node drainage, or secret inspection permissions.
> 3. **Non-Repudiation Audit Logging:** Every executed or rejected action is logged with timestamp, user ID, and diff payload.

#### Q4: What is the difference between Exit Code 137 and Exit Code 143 in Kubernetes?
> **Answer:** 
> * **Exit Code 137 (`128 + 9` = SIGKILL):** Triggered when the Linux kernel Out-Of-Memory (OOM) killer forcibly terminates the container because it exceeded its CGroup memory limits (`OOMKilled`).
> * **Exit Code 143 (`128 + 15` = SIGTERM):** Triggered when Kubernetes gracefully terminates a pod (e.g. during deployment rollout or scaling down).

#### Q5: How does InfraGPT handle API rate limits and network outages during a demo?
> **Answer:** InfraGPT uses a hybrid dual-brain architecture. If external LLM API keys or quotas fail (HTTP 429 / 503), the orchestrator automatically activates its built-in deterministic SRE diagnostic compiler, ensuring 100% demo resilience and zero latency.
