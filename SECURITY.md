# Security & Vulnerability Disclosure Policy

InfraGPT treats cluster safety and access control as first-class architectural constraints.

---

### Security Guardrails

1. **Mandatory Human Authorization:** No write or destructive operation (`scale_deployment`, `patch_deployment_resources`, `set_deployment_env`, `rollout_restart`, `delete_pod`) is executed autonomously without explicit cryptographic HITL approval.
2. **Least Privilege Principle:** The agent operates with scoped `ClusterRole` permissions, preventing cluster takeover.
3. **Secret Isolation:** Kubernetes secret discovery is disabled by default to prevent secret exfiltration into LLM token contexts.

---

### Reporting Security Issues

To report a vulnerability or privilege escalation bug, please open a private security advisory or contact the project maintainers directly.
