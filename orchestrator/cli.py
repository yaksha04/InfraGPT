"""
Interactive Terminal CLI for InfraGPT
Provides a Rich, dark-terminal chat interface with live tool calling feedback and interactive HITL approvals.
"""

import sys
import os
from typing import Dict, Any

# Ensure workspace paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.table import Table

from agent import InfraGPTAgent
from hitl import HITLApprovalGate
from tools_bridge import get_k8s_adapter

console = Console()


def render_banner():
    banner_text = (
        "[bold cyan]🌐 InfraGPT[/bold cyan] — [italic green]Natural Language Kubernetes Manager via MCP[/italic green]\n"
        "[dim]Powered by FastMCP + Google Gemini + Human-in-the-Loop Safety Gate[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan", padding=(1, 2)))


def on_tool_call_handler(tool_name: str, args: Dict[str, Any]):
    """Live visual indicator when AI invokes an MCP tool."""
    console.print(f"  [dim cyan]⚡ Calling MCP Tool:[/dim cyan] [bold yellow]{tool_name}[/bold yellow] [dim]({args})[/dim]")


def approval_callback_handler(tool_name: str, args: Dict[str, Any]) -> bool:
    """Prompts human user to approve destructive/mutating write operations."""
    console.print()
    approval_msg = HITLApprovalGate.format_approval_request(tool_name, args)
    console.print(Panel(approval_msg, title="🚨 HITL SECURITY GATE", border_style="yellow"))
    
    confirmed = Confirm.ask("[bold yellow]Do you authorize this action?[/bold yellow]", default=False)
    if confirmed:
        console.print("[bold green]✔ Action Approved by Engineer.[/bold green]\n")
    else:
        console.print("[bold red]✖ Action Rejected by Engineer.[/bold red]\n")
    return confirmed


def main():
    render_banner()
    
    agent = InfraGPTAgent()
    adapter = get_k8s_adapter()
    status = adapter.get_status()

    # Display Cluster Connection Status Badge
    mode_badge = "[bold green]LIVE K8S[/bold green]" if adapter.is_live else "[bold yellow]MOCK CLUSTER (Dev)[/bold yellow]"
    llm_badge = "[bold green]GEMINI 1.5 FLASH[/bold green]" if agent.is_live_llm else "[bold yellow]SMART SRE ENGINE[/bold yellow]"
    
    console.print(f"📡 [bold]Cluster Mode:[/bold] {mode_badge} | 🧠 [bold]AI Brain:[/bold] {llm_badge}")
    console.print("[dim]Type [bold white]'exit'[/bold white] or [bold white]'quit'[/bold white] to leave. Type [bold white]'help'[/bold white] for suggestions.\n[/dim]")

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]👤 You[/bold cyan]")
            if not user_input.strip():
                continue

            if user_input.strip().lower() in ["exit", "quit", "q"]:
                console.print("[italic cyan]Exiting InfraGPT. Have a great day![/italic cyan]")
                break

            console.print("\n[dim]Thinking & inspecting cluster...[/dim]")
            response = agent.send_message(
                user_prompt=user_input,
                approval_callback=approval_callback_handler,
                on_tool_call=on_tool_call_handler
            )

            console.print("\n[bold green]🤖 InfraGPT:[/bold green]")
            console.print(Markdown(response))
            console.print("\n" + "─" * 60 + "\n")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[italic cyan]Session ended.[/italic cyan]")
            break


if __name__ == "__main__":
    main()
