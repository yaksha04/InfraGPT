# InfraGPT Production Deployment & Readiness Checklist

Before deploying InfraGPT to live Kubernetes production clusters, verify the following operational gates:

---

### 1. Security & Access Control
- [ ] **Dedicated ServiceAccount:** Ensure `infragpt-agent-sa` is used (never run as `default` or `cluster-admin`).
- [ ] **RBAC Verification:** Test that `ClusterRole` denies secret extraction and namespace deletion.
- [ ] **NetworkPolicy Isolation:** Verify ingress/egress rules are applied in `production` namespace.

---

### 2. Resilience & Redundancy
- [ ] **Gemini API Key:** Ensure `GEMINI_API_KEY` is loaded securely via Kubernetes Secret or environment variable.
- [ ] **Offline Fallback Validation:** Verify that if the external API fails, the SRE rule engine answers without error.
- [ ] **Persistent Audit Logs:** Configure PostgreSQL volume mount for durable audit logging.

---

### 3. Monitoring & Telemetry
- [ ] **Prometheus Exporters:** Verify metrics endpoints respond on port `8888`.
- [ ] **Readiness & Liveness Probes:** Verify container health checks in `docker-compose.yml` and Kubernetes manifests.
