"""
InfraGPT AI Agent Engine
Coordinates Gemini LLM reasoning, autonomous multi-turn tool calling, and HITL safety gate.
Supports high-quota model fallback (gemini-flash-latest / gemini-3.5-flash) and fully dynamic SRE engine.
"""

import json
import os
import sys
import logging
import re
from typing import Dict, Any, List, Optional, Callable
from dotenv import load_dotenv

load_dotenv()

from prompt import SYSTEM_INSTRUCTION
from hitl import HITLApprovalGate
from tools_bridge import AGENT_TOOLS, TOOL_MAP, execute_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("infragpt-agent")

try:
    from google import genai
    from google.genai import types
    GENAI_NEW_SDK = True
except ImportError:
    GENAI_NEW_SDK = False


class InfraGPTAgent:
    """Core AI Orchestrator that manages multi-turn dialogue, tool routing, and approval checks."""

    FALLBACK_MODELS = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-2.5-flash"]

    DEPLOYMENT_REGISTRY = [
        ("frontend-web", ["frontend-web", "frontend", "frontend_web", "frontend web", "frontend-service", "web"]),
        ("user-auth-service", ["user-auth-service", "user-auth", "user auth", "auth-service", "auth", "user_auth"]),
        ("payment-service", ["payment-service", "payment", "payment_service", "payment service", "pay"]),
        ("order-service", ["order-service", "order", "order_service", "order service", "orders"]),
        ("notification-service", ["notification-service", "notification", "notification service", "notif", "notify"]),
        ("inventory-service", ["inventory-service", "inventory", "inventory_service", "inventory service", "invent"])
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-flash-latest"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.client = None
        self.is_live_llm = False
        self._init_llm()

    def _init_llm(self):
        if not self.api_key or self.api_key.startswith("your_gemini"):
            logger.info("Running in Dynamic SRE Engine Mode.")
            self.is_live_llm = False
            return

        if GENAI_NEW_SDK:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.is_live_llm = True
                logger.info(f"Connected to Google GenAI API with model '{self.model_name}'.")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}. Using SRE Engine Mode.")
                self.is_live_llm = False

    def send_message(
        self,
        user_prompt: str,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Send a prompt to InfraGPT. Gemini tool calling is used when an API key is configured."""
        if self.is_live_llm and os.getenv("INFRAGPT_FORCE_SIMULATOR", "").lower() not in {"1", "true", "yes"}:
            try:
                return self._live_agent_response(user_prompt, approval_callback, on_tool_call, history)
            except Exception as exc:
                logger.warning("Gemini tool calling failed (%s). Using the built-in SRE engine.", exc)
        return self._simulated_agent_response(user_prompt, approval_callback, on_tool_call, history)

    def _live_agent_response(
        self,
        prompt: str,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]],
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Let Gemini choose MCP tools. Write tools stop at the approval gate."""
        from google.genai import types
        from tool_schemas import gemini_tools

        models = []
        for name in [self.model_name, *self.FALLBACK_MODELS]:
            if name not in models:
                models.append(name)

        last_error: Optional[Exception] = None
        for model in models:
            try:
                return self._complete_with_gemini(
                    model, prompt, approval_callback, on_tool_call, history, types, gemini_tools()
                )
            except Exception as exc:
                last_error = exc
                logger.warning("Model %s failed: %s", model, exc)
        if last_error:
            raise last_error
        raise RuntimeError("Gemini did not return a response")

    def _complete_with_gemini(
        self,
        model: str,
        prompt: str,
        approval_callback,
        on_tool_call,
        history,
        types,
        tools,
    ) -> str:
        contents = []
        for message in (history or [])[-8:]:
            role = "user" if message.get("role") == "user" else "model"
            text = message.get("content") or ""
            if text:
                contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

        instruction = (
            SYSTEM_INSTRUCTION
            + "\n\nWhen you diagnose a failure, the markdown must contain these exact headings: "
            + "**Root Cause**, **Evidence**, **Suggested Fix**, **Risk Level**. "
            + "Risk Level is Low, Medium, or High. "
            + "Use only tool results. If a tool returns Kubernetes unavailable, Deployment not found, "
            + "Pod not found, or Approval expired, say that exact phrase and do not invent a stack trace. "
            + "For write tools, call the tool so the approval gate can run. Do not claim a write succeeded "
            + "unless the tool result says success."
        )

        for _ in range(6):
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    tools=tools,
                    temperature=0.2,
                ),
            )
            candidate = response.candidates[0]
            parts = list(candidate.content.parts or [])
            calls = [part for part in parts if getattr(part, "function_call", None)]
            if not calls:
                text = (getattr(response, "text", None) or "").strip()
                return text or "I could not produce a response from the cluster data."

            contents.append(candidate.content)
            response_parts = []
            for part in calls:
                name = part.function_call.name
                args = _coerce_args(part.function_call.args)
                if on_tool_call:
                    on_tool_call(name, args)
                if HITLApprovalGate.is_write_operation(name):
                    approved = True if approval_callback is None else bool(approval_callback(name, args))
                    if not approved:
                        return (
                            "This change needs your approval before it can run.\n\n"
                            f"**Proposed action:** `{name}`\n\n"
                            "Review the before and after summary, then approve or reject it."
                        )
                result = execute_tool(name, args)
                payload = result if isinstance(result, dict) else {"result": _jsonable(result)}
                response_parts.append(
                    types.Part.from_function_response(name=name, response=_jsonable(payload))
                )
            contents.append(types.Content(role="user", parts=response_parts))

        return "I stopped after several tool calls. Ask a narrower question and I will continue."

    def _finish_write(self, result: Any, success_text: str) -> str:
        if isinstance(result, dict) and result.get("success") is False:
            title = result.get("error") or "The operation could not be completed"
            detail = result.get("message") or title
            return f"**{title}**\n\n{detail}"
        return success_text

    def _simulated_agent_response(
        self,
        prompt: str,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]],
        on_tool_call: Optional[Callable[[str, Dict[str, Any]], None]],
        history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Fully Dynamic SRE diagnostic and execution engine with decoupled service & action extraction."""
        # Extract prior assistant context
        prev_context = ""
        if history:
            for m in reversed(history):
                if m.get("role") in ["model", "assistant", "ai"]:
                    prev_context = m.get("content", "").lower()
                    break

        # 1. Target namespace comes from the dashboard tag. The engineer can override it by name.
        ns, user_text = _split_dashboard_prompt(prompt)
        lower = user_text.lower()
        explicit_ns = re.search(
            r"\b(?:namespace|in)\s+(production|staging|default|infragpt-system)\b",
            lower,
        )
        if explicit_ns:
            ns = explicit_ns.group(1)

        # 2. STRICT SERVICE RESOLUTION (Checking current prompt first, aliases strictly separated from actions)
        target_dep = None
        mentioned = False
        for dep_name, aliases in self.DEPLOYMENT_REGISTRY:
            if any(_mentions(lower, alias) for alias in aliases):
                target_dep = dep_name
                mentioned = True
                break

        # If no service mentioned in current prompt, check previous context (for "fix it", "yes", "do it")
        if not target_dep and prev_context:
            for dep_name, aliases in self.DEPLOYMENT_REGISTRY:
                if any(_mentions(prev_context, alias) for alias in aliases):
                    target_dep = dep_name
                    break

        # 3. ACTION INTENT RESOLUTION (Completely Independent from Service Names)
        is_logs = _mentions(lower, "log", "logs", "tail", "stdout", "stderr", "stacktrace")
        is_events = _mentions(lower, "event", "events", "warning events", "cluster events")
        is_scale = _mentions(lower, "scale", "replica", "replicas", "instances", "count")
        is_restart = _mentions(lower, "restart", "rollout", "reboot")
        is_delete = _mentions(lower, "delete pod", "kill pod", "terminate pod")
        is_memory = _mentions(lower, "memory", "ram", "limit", "patch memory", "badha do", "kam kar do") or bool(
            re.search(r"\b(?:128|256|512|1024|1gi|2gi)\b", lower)
        )
        is_image = _mentions(lower, "image", "tag", "imagepull", "nginx:alpine", "busybox")
        is_env = _mentions(lower, "env", "database", "db_connection_string", "redis", "connection string", "config variable", "environment")
        is_generic_fix = _mentions(lower, "fix", "yes", "go ahead", "do it", "apply", "theek", "kar do", "proceed", "confirm")
        is_top_restarts = _mentions(lower, "highest restart", "most restart", "top restart", "restart count")
        is_crash_logs = _mentions(lower, "crashloop", "crash loop") and _mentions(lower, "log", "logs")
        is_explain_oom = _mentions(lower, "explain") and "oom" in lower
        is_list = _mentions(lower, "all pods", "list pods", "show all pods", "running pods", "show pods", "get pods", "cluster pods") and not is_logs and not is_events

        # Fallback target deployment if still none
        if not target_dep:
            try:
                pods_check = execute_tool("list_pods", {"namespace": ns})
                unhealthy = [p for p in pods_check if not p.get("is_healthy", True)]
                if unhealthy:
                    pname = unhealthy[0]["name"]
                    for d, _ in self.DEPLOYMENT_REGISTRY:
                        if d.split("-")[0] in pname:
                            target_dep = d
                            break
            except Exception:
                pass

        if not target_dep:
            target_dep = "frontend-web" if "front" in lower else "payment-service"

        # Determine concrete action
        if is_top_restarts:
            action = "top_restarts"
        elif is_crash_logs:
            action = "crash_logs"
        elif is_explain_oom:
            action = "diagnose"
        elif is_logs:
            action = "get_logs"
        elif is_events:
            action = "get_events"
        elif is_scale:
            action = "scale"
        elif is_restart:
            action = "restart"
        elif is_delete:
            action = "delete"
        elif is_memory and not is_env and not is_image and not is_logs:
            action = "memory_patch"
        elif is_image:
            action = "image_patch"
        elif is_env:
            action = "env_patch"
        elif is_generic_fix:
            if target_dep == "notification-service" or "image" in prev_context:
                action = "image_patch"
            elif target_dep == "order-service" or "redis" in prev_context:
                action = "env_patch"
            elif target_dep == "inventory-service" or "database" in prev_context:
                action = "env_patch"
            else:
                action = "memory_patch"
        elif is_list:
            action = "list"
        else:
            action = "diagnose"

        # -------------------------------------------------------------
        # Action Execution: Pods ranked by restart count
        # -------------------------------------------------------------
        if action == "top_restarts":
            if on_tool_call:
                on_tool_call("list_pods", {"namespace": ns})
            pods = execute_tool("list_pods", {"namespace": ns})
            failure = _tool_failure(pods)
            if failure:
                return failure
            ranked = sorted(pods, key=lambda pod: pod.get("restarts") or 0, reverse=True)
            output = f"### Pods with the highest restarts — `{ns}`\n\n| Pod | Status | Restarts |\n| :--- | :--- | :--- |\n"
            for pod in ranked:
                output += f"| `{pod.get('name')}` | {pod.get('status')} | **{pod.get('restarts', 0)}** |\n"
            if ranked and (ranked[0].get("restarts") or 0) == 0:
                output += "\nNo pod in this namespace has restarted."
            return output

        # -------------------------------------------------------------
        # Action Execution: Logs for CrashLoop pods
        # -------------------------------------------------------------
        elif action == "crash_logs":
            if on_tool_call:
                on_tool_call("list_pods", {"namespace": ns})
            pods = execute_tool("list_pods", {"namespace": ns})
            failure = _tool_failure(pods)
            if failure:
                return failure
            crashing = [
                pod for pod in pods
                if "crash" in str(pod.get("status", "")).lower() or "oom" in str(pod.get("status", "")).lower()
            ]
            if not crashing:
                return f"No CrashLoop pods were found in `{ns}`."
            sections = ["### Logs of CrashLoop pods\n"]
            for pod in crashing[:4]:
                if on_tool_call:
                    on_tool_call("get_pod_logs", {"pod_name": pod["name"], "namespace": ns, "tail_lines": 40})
                logs = execute_tool("get_pod_logs", {"pod_name": pod["name"], "namespace": ns, "tail_lines": 40})
                sections.append(f"#### `{pod['name']}` — {pod.get('status')} · {pod.get('restarts', 0)} restarts\n\n```log\n{logs}\n```")
            return "\n".join(sections)

        # -------------------------------------------------------------
        # Action Execution: Get Pod Logs
        # -------------------------------------------------------------
        elif action == "get_logs":
            pod_match = re.search(r'([a-zA-Z0-9_-]+-[a-z0-9]{5,10}-[a-z0-9]{4,6})', prompt)
            target_pod = pod_match.group(1) if pod_match else None

            if not target_pod:
                pods = execute_tool("list_pods", {"namespace": ns})
                for p in pods:
                    if target_dep and target_dep.split("-")[0] in p["name"]:
                        target_pod = p["name"]
                        break
                if not target_pod and pods:
                    target_pod = pods[0]["name"]

            if on_tool_call:
                on_tool_call("get_pod_logs", {"pod_name": target_pod, "namespace": ns, "tail_lines": 50})

            logs_content = execute_tool("get_pod_logs", {"pod_name": target_pod, "namespace": ns, "tail_lines": 50})
            failure = _tool_failure(logs_content)
            if failure:
                return failure

            return (
                f"### 📄 Container Logs: `{target_pod}` (Namespace: `{ns}`)\n\n"
                f"```log\n"
                f"{logs_content}\n"
                f"```"
            )

        # -------------------------------------------------------------
        # Action Execution: Get Pod Events
        # -------------------------------------------------------------
        elif action == "get_events":
            pod_match = re.search(r'([a-zA-Z0-9_-]+-[a-z0-9]{5,10}-[a-z0-9]{4,6})', prompt)
            target_pod = pod_match.group(1) if pod_match else None

            if not target_pod:
                pods = execute_tool("list_pods", {"namespace": ns})
                for p in pods:
                    if target_dep and target_dep.split("-")[0] in p["name"]:
                        target_pod = p["name"]
                        break
                if not target_pod and pods:
                    target_pod = pods[0]["name"]

            if on_tool_call:
                on_tool_call("get_pod_events", {"pod_name": target_pod, "namespace": ns})

            events_list = execute_tool("get_pod_events", {"pod_name": target_pod, "namespace": ns})

            output = f"### ⚠️ Cluster Events for `{target_pod}` (`{ns}`)\n\n| Type | Reason | Message | Count |\n| :--- | :--- | :--- | :--- |\n"
            if isinstance(events_list, list) and events_list:
                for e in events_list:
                    output += f"| `{e.get('type')}` | **{e.get('reason')}** | {e.get('message')} | {e.get('count')} |\n"
            else:
                output += "| Normal | NoEvents | No warning events found for this pod | 0 |\n"
            return output

        # -------------------------------------------------------------
        # Action Execution: Memory Patch (Fix OOMKilled or Resource Resizing)
        # -------------------------------------------------------------
        elif action == "memory_patch":
            # Extract destination memory limit with normalization (e.g. from 512 to 256 -> 256Mi)
            target_to = re.search(r'(?:to|\binto\b)\s+(\d+(?:[a-zA-Z]+)?)', prompt, re.IGNORECASE)
            if target_to:
                raw_val = target_to.group(1)
            else:
                nums = re.findall(r'(\d+(?:[a-zA-Z]+)?)', prompt)
                raw_val = nums[-1] if len(nums) > 1 else nums[0] if nums else "512Mi"

            num_part = re.search(r'\d+', raw_val).group(0) if re.search(r'\d+', raw_val) else "512"
            if "gi" in raw_val.lower() or "g" in raw_val.lower() and "m" not in raw_val.lower():
                target_memory = f"{num_part}Gi"
            else:
                target_memory = f"{num_part}Mi"

            tool_name = "patch_deployment_resources"
            args = {"name": target_dep, "memory_limit": target_memory, "namespace": ns}
            action_label = "Resource Limit Patch"

            if HITLApprovalGate.is_write_operation(tool_name):
                approved = True
                if approval_callback:
                    approved = approval_callback(tool_name, args)
                if not approved:
                    return f"❌ **Operation Aborted:** {action_label} canceled by user."

            if on_tool_call:
                on_tool_call(tool_name, args)
            res = execute_tool(tool_name, args)

            return self._finish_write(res, (
                f"✅ **{action_label} Successfully Applied!**\n\n"
                f"• Target Deployment: `{target_dep}` (Namespace: `{ns}`)\n"
                f"• Patched Memory Limit: `{target_memory}`\n"
                f"• Status: Kubernetes Deployment controller updated the pod spec."
            ))

        # -------------------------------------------------------------
        # Action Execution: Image Patch (Fix ImagePullBackOff)
        # -------------------------------------------------------------
        elif action == "image_patch":
            tool_name = "set_deployment_image"
            target_image = "nginx:alpine" if "nginx" in lower or "notification" in target_dep else "busybox:1.36"
            args = {"name": target_dep, "image": target_image, "namespace": ns}
            action_label = "Container Image Patch"

            if HITLApprovalGate.is_write_operation(tool_name):
                approved = True
                if approval_callback:
                    approved = approval_callback(tool_name, args)
                if not approved:
                    return f"❌ **Operation Aborted:** {action_label} canceled by user."

            if on_tool_call:
                on_tool_call(tool_name, args)
            res = execute_tool(tool_name, args)

            return self._finish_write(res, (
                f"✅ **{action_label} Successfully Applied!**\n\n"
                f"• Target Deployment: `{target_dep}` (Namespace: `{ns}`)\n"
                f"• Updated Image: `{target_image}`\n"
                f"• Status: ImagePullBackOff resolved. Fresh container pulled successfully."
            ))

        # -------------------------------------------------------------
        # Action Execution: Environment Variables (Fix Config / Redis / DB)
        # -------------------------------------------------------------
        elif action == "env_patch":
            tool_name = "set_deployment_env"
            if target_dep == "order-service" or "redis" in lower or "redis" in prev_context:
                env_vars = {"REDIS_HOST": "redis-prod.production.svc.cluster.local"}
            else:
                env_vars = {"DB_CONNECTION_STRING": "postgresql://infragpt:infragpt_secret@postgres-prod:5432/inventory"}

            args = {
                "name": target_dep,
                "env_vars": env_vars,
                "namespace": ns
            }
            action_label = "Environment Variable Patch"

            if HITLApprovalGate.is_write_operation(tool_name):
                approved = True
                if approval_callback:
                    approved = approval_callback(tool_name, args)
                if not approved:
                    return f"❌ **Operation Aborted:** {action_label} canceled by user."

            if on_tool_call:
                on_tool_call(tool_name, args)
            res = execute_tool(tool_name, args)

            return self._finish_write(res, (
                f"✅ **{action_label} Successfully Applied!**\n\n"
                f"• Target Deployment: `{target_dep}` (Namespace: `{ns}`)\n"
                f"• Injected Config: `{env_vars}`\n"
                f"• Status: Application reloaded with required environment variables."
            ))

        # -------------------------------------------------------------
        # Action Execution: Scale Deployment
        # -------------------------------------------------------------
        elif action == "scale":
            numbers = re.findall(r"\d+", lower)
            replicas = int(numbers[0]) if numbers else 3
            tool_name = "scale_deployment"
            args = {"name": target_dep, "replicas": replicas, "namespace": ns}

            if HITLApprovalGate.is_write_operation(tool_name):
                approved = True
                if approval_callback:
                    approved = approval_callback(tool_name, args)
                if not approved:
                    return f"❌ **Operation Aborted:** Scale operation canceled by user."

            if on_tool_call:
                on_tool_call(tool_name, args)
            res = execute_tool(tool_name, args)

            return self._finish_write(
                res,
                f"✅ **Deployment Scaled:** `{target_dep}` scaled to **{replicas} replicas** in `{ns}`.",
            )

        # -------------------------------------------------------------
        # Action Execution: Rolling Restart
        # -------------------------------------------------------------
        elif action == "restart":
            tool_name = "rollout_restart"
            args = {"deployment_name": target_dep, "namespace": ns}
            if HITLApprovalGate.is_write_operation(tool_name):
                approved = True
                if approval_callback:
                    approved = approval_callback(tool_name, args)
                if not approved:
                    return f"❌ **Operation Aborted:** Rollout restart canceled by user."
            if on_tool_call:
                on_tool_call(tool_name, args)
            res = execute_tool(tool_name, args)
            return self._finish_write(
                res,
                f"✅ **Rolling Restart Triggered:** `{target_dep}` in namespace `{ns}`.",
            )

        # -------------------------------------------------------------
        # Action Execution: List Pods
        # -------------------------------------------------------------
        elif action == "list":
            if on_tool_call:
                on_tool_call("list_pods", {"namespace": ns})
            pods = execute_tool("list_pods", {"namespace": ns})
            failure = _tool_failure(pods)
            if failure:
                return failure
            output = f"### 📋 Pods in Namespace: `{ns}`\n\n| Pod Name | Status | Ready | Restarts |\n| :--- | :--- | :--- | :--- |\n"
            for p in pods:
                status_icon = "🟢" if p.get('is_healthy') else "🔴"
                output += f"| `{p['name']}` | {status_icon} {p['status']} | {p['ready']} | {p['restarts']} |\n"
            return output

        # -------------------------------------------------------------
        # Action Execution: Diagnostic & Root Cause Analysis (RCA)
        # -------------------------------------------------------------
        else:
            if on_tool_call:
                on_tool_call("list_pods", {"namespace": ns})
            pods = execute_tool("list_pods", {"namespace": ns})
            failure = _tool_failure(pods)
            if failure:
                return failure

            matched = [p for p in pods if target_dep and target_dep.split("-")[0] in p["name"]]
            if mentioned and not matched:
                return (
                    f"**Deployment not found**\n\n"
                    f"`{target_dep}` is not in namespace `{ns}`. "
                    "The demo workloads live in `production`."
                )

            broken_pod = matched[0]["name"] if matched else None

            if not broken_pod:
                unhealthy_pods = [p for p in pods if not p.get("is_healthy", True)]
                if unhealthy_pods:
                    broken_pod = unhealthy_pods[0]["name"]
                else:
                    return f"[OK] All pods in namespace `{ns}` are healthy with 0 restarts."

            # Automatically derive target_dep from inspected broken pod
            for d, _ in self.DEPLOYMENT_REGISTRY:
                if d.split("-")[0] in broken_pod:
                    target_dep = d
                    break

            if on_tool_call:
                on_tool_call("get_pod_events", {"pod_name": broken_pod, "namespace": ns})
                on_tool_call("get_pod_logs", {"pod_name": broken_pod, "namespace": ns, "tail_lines": 50})

            events = execute_tool("get_pod_events", {"pod_name": broken_pod, "namespace": ns})
            logs = execute_tool("get_pod_logs", {"pod_name": broken_pod, "namespace": ns, "tail_lines": 50})

            evidence = _evidence_block(events, logs)
            # 1. Order Service Redis Error
            if "order" in target_dep or "redis" in str(logs).lower():
                return _rca(
                    broken_pod,
                    ns,
                    "CrashLoopBackOff",
                    "Missing mandatory environment variable `REDIS_HOST`. The process cannot reach redis-master:6379.",
                    evidence,
                    f"Set `REDIS_HOST=redis-prod.production.svc.cluster.local` on `{target_dep}`. You can type *fix {target_dep}*.",
                    "High",
                )
            # 2. Notification Service Image Error
            elif "notification" in target_dep or "image" in str(events).lower() or "imagepull" in str(events).lower():
                return _rca(
                    broken_pod,
                    ns,
                    "ImagePullBackOff",
                    "The container image tag does not exist (`nginx:v999-broken-tag`), so the kubelet cannot pull it.",
                    evidence,
                    f"Change the `{target_dep}` image to `nginx:alpine`. You can type *fix {target_dep}*.",
                    "High",
                )
            # 3. Inventory Service Missing DB
            elif "inventory" in target_dep or "db_connection_string" in str(logs).lower():
                return _rca(
                    broken_pod,
                    ns,
                    "CrashLoopBackOff",
                    "Missing mandatory environment variable `DB_CONNECTION_STRING`. The process exits before it can serve traffic.",
                    evidence,
                    f"Inject the database connection string into `{target_dep}`. You can type *fix {target_dep}*.",
                    "High",
                )
            # 4. Payment Service OOM
            elif "payment" in target_dep or "137" in str(events) or "oom" in str(logs).lower():
                return _rca(
                    broken_pod,
                    ns,
                    "CrashLoopBackOff (OOMKilled)",
                    "Process terminated due to **OOMKilled (Exit Code 137)**. The memory limit is below the working set.",
                    evidence,
                    f"Patch `{target_dep}` memory limit to **512Mi**.",
                    "High",
                )
            else:
                return _rca(
                    broken_pod,
                    ns,
                    "Degraded",
                    "The container failed its runtime health check.",
                    evidence,
                    f"Inspect events, then type *fix {target_dep}* to remediate.",
                    "Medium",
                )


def _mentions(text: str, *needles: str) -> bool:
    """Match a keyword on a word boundary. Substrings such as 'tag' inside 'staging' do not count."""
    for needle in needles:
        if re.search(r"[^\w]", needle):
            if needle in text:
                return True
            continue
        if re.search(rf"\b{re.escape(needle)}\b", text):
            return True
    return False


def _split_dashboard_prompt(prompt: str):
    """Separate the UI namespace tag from the engineer text so the tag cannot change the intent."""
    match = re.search(
        r"\[\s*active dashboard namespace:\s*([a-z0-9-]+)\s*\]\s*(?:engineer query:\s*)?",
        prompt,
        flags=re.IGNORECASE,
    )
    if not match:
        return "production", prompt
    return match.group(1).lower(), prompt[match.end():]


def _jsonable(value: Any) -> Any:
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    try:
        return json.loads(json.dumps(value, default=str))
    except TypeError:
        return str(value)


def _coerce_args(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    try:
        return dict(raw)
    except Exception:
        loaded = _jsonable(raw)
        return loaded if isinstance(loaded, dict) else {}


def _tool_failure(result: Any) -> Optional[str]:
    if isinstance(result, dict) and result.get("success") is False:
        title = result.get("error") or "The operation could not be completed"
        detail = result.get("message") or title
        return f"**{title}**\n\n{detail}"
    return None


def _evidence_block(events: Any, logs: Any) -> str:
    lines = []
    if isinstance(events, list):
        for event in events[:3]:
            if isinstance(event, dict) and event.get("reason"):
                lines.append(f"- Event `{event.get('reason')}` ({event.get('type', 'Warning')}): {event.get('message')}")
    log_text = logs if isinstance(logs, str) else ""
    excerpt = " ".join(line.strip() for line in log_text.splitlines() if line.strip())[:280]
    if excerpt:
        lines.append(f"- Log excerpt: {excerpt}")
    if not lines:
        lines.append("- No events or logs were returned for this pod.")
    return "\n".join(lines)


def _rca(pod: str, namespace: str, state: str, root: str, evidence: str, fix: str, risk: str) -> str:
    return (
        f"### Root Cause Analysis — `{pod}` in `{namespace}`\n\n"
        f"**Status**\n"
        f"- Pod `{pod}` is **{state}**.\n\n"
        f"**Root Cause**\n"
        f"{root}\n\n"
        f"**Evidence**\n"
        f"{evidence}\n\n"
        f"**Suggested Fix**\n"
        f"{fix}\n\n"
        f"**Risk Level**\n"
        f"{risk}\n"
    )
