"""
Human-in-the-Loop (HITL) Safety Gate for InfraGPT
Enforces explicit human approval for all state-mutating Kubernetes operations.
"""

from typing import Dict, Any, Tuple


class HITLApprovalGate:
    """Intercepts tool executions and determines if human authorization is mandatory."""

    WRITE_TOOLS = {
        "scale_deployment": "Scaling deployment replica count",
        "patch_deployment_resources": "Patching CPU / Memory resource limits",
        "set_deployment_env": "Setting environment variables on deployment",
        "set_deployment_image": "Updating deployment container image tag",
        "rollout_restart": "Triggering rolling restart of deployment pods",
        "delete_pod": "Terminating active pod instance"
    }

    @classmethod
    def is_write_operation(cls, tool_name: str) -> bool:
        """Check if a tool modifies cluster state."""
        return tool_name in cls.WRITE_TOOLS

    @classmethod
    def format_approval_request(cls, tool_name: str, args: Dict[str, Any]) -> str:
        """Generate human-readable confirmation message before execution."""
        action_desc = cls.WRITE_TOOLS.get(tool_name, "Cluster Modification")
        
        if tool_name == "scale_deployment":
            return (
                f"⚠️ [bold yellow]APPROVAL REQUIRED[/bold yellow]: {action_desc}\n"
                f"• Target Deployment: [bold cyan]{args.get('name')}[/bold cyan]\n"
                f"• Namespace: [bold cyan]{args.get('namespace', 'default')}[/bold cyan]\n"
                f"• Target Replicas: [bold green]{args.get('replicas')}[/bold green]\n"
                f"Do you want to proceed?"
            )
        elif tool_name == "patch_deployment_resources":
            return (
                f"⚠️ [bold yellow]APPROVAL REQUIRED[/bold yellow]: {action_desc}\n"
                f"• Target Deployment: [bold cyan]{args.get('name')}[/bold cyan]\n"
                f"• Namespace: [bold cyan]{args.get('namespace', 'default')}[/bold cyan]\n"
                f"• New Memory Limit: [bold green]{args.get('memory_limit', 'Unchanged')}[/bold green]\n"
                f"• New CPU Limit: [bold green]{args.get('cpu_limit', 'Unchanged')}[/bold green]\n"
                f"Do you want to apply this resource patch?"
            )
        elif tool_name == "rollout_restart":
            return (
                f"⚠️ [bold yellow]APPROVAL REQUIRED[/bold yellow]: {action_desc}\n"
                f"• Target Deployment: [bold cyan]{args.get('deployment_name')}[/bold cyan]\n"
                f"• Namespace: [bold cyan]{args.get('namespace', 'default')}[/bold cyan]\n"
                f"Proceed with rolling restart?"
            )
        elif tool_name == "delete_pod":
            return (
                f"⚠️ [bold red]APPROVAL REQUIRED (DESTRUCTIVE)[/bold red]: {action_desc}\n"
                f"• Pod Name: [bold red]{args.get('pod_name')}[/bold red]\n"
                f"• Namespace: [bold cyan]{args.get('namespace', 'default')}[/bold cyan]\n"
                f"Are you sure you want to delete this pod?"
            )
        else:
            return f"⚠️ [bold yellow]APPROVAL REQUIRED[/bold yellow] for {tool_name} with arguments {args}. Proceed?"
