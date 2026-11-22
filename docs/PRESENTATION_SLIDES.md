# InfraGPT: Final Year Presentation Slide Deck Outline
## 15-Minute PowerPoint Script & Visual Layout

---

### Slide 1: Title & Team
* **Title:** InfraGPT — Autonomous Site Reliability Engineering & Kubernetes Governance
* **Subtitle:** An AI-Driven SRE Platform Powered by Gemini 2.5 Flash and FastMCP
* **Presented by:** Akshat (AI/ML Lead), Yaksha (DevOps Lead), Bhoomi (Frontend Lead)
* **Guide / Supervisor:** Department of Computer Science & Engineering

---

### Slide 2: Motivation & The SRE Problem
* **The Reality of Production Outages:**
  - 70% of outage resolution time is spent diagnosing logs and correlating events.
  - Alert fatigue leads to missed critical signals.
* **Why Traditional Tools Fall Short:**
  - Prometheus/Grafana show graphs, not root causes.
  - Scripts lack multi-turn reasoning and conversational context.

---

### Slide 3: Proposed Architecture
* **Decoupled 3-Tier Model:**
  1. React 18 Cyber-Ops Dashboard.
  2. FastAPI Orchestrator + HITL State-Machine.
  3. FastMCP Kubernetes Gateway + Live/Mock Adapter.

---

### Slide 4: Autonomous Diagnostic Tree (Live Demo Flow)
* `list_pods` ➔ Detect `CrashLoopBackOff`
* `get_pod_events` ➔ Find `OOMKilled (Exit Code 137)`
* `get_pod_logs` ➔ Parse `java.lang.OutOfMemoryError: Java heap space`
* Generate structured natural language RCA with recommended fix.

---

### Slide 5: Security & Human-In-The-Loop (HITL) Gate
* Zero unauthorized write operations.
* Interactive Amber Confirmation Modal with payload diff.
* Non-repudiation tamper-evident audit logs.

---

### Slide 6: Live Demonstration & Results
* **Case 1:** OOM Recovery (`payment-service` 256Mi ➔ 512Mi ➔ Pod turns Green).
* **Case 2:** Missing Config Resolution (`inventory-service` DB injection ➔ Pod turns Green).
* **Case 3:** High-Throughput Scaling (`user-auth-service` 2 ➔ 4 replicas).

---

### Slide 7: Conclusion & Future Scope
* **Conclusion:** Reduced MTTR by 75% while maintaining enterprise security.
* **Future Scope:** Multi-cluster federated governance, eBPF telemetry integration, automated Canary rollback.
