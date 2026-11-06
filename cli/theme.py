import os
import sys
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table

# Custom Dark Obsidian & Neon Cyber Theme
custom_theme = Theme({
    "info": "bold cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "master": "bold magenta",
    "node": "bold blue",
    "subdued": "dim white"
})

# Ensure safe console output even on Windows cp1252 terminals
console = Console(theme=custom_theme, safe_box=True)


def use_color():
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def paint(text, color_tag="info"):
    return f"[{color_tag}]{text}[/{color_tag}]"


def success(text):
    console.print(Panel(f"[bold green]OK:[/bold green] {text}", border_style="green", expand=False))


def info(text):
    console.print(Panel(f"[bold cyan]INFO:[/bold cyan] {text}", border_style="cyan", expand=False))


def warning(text):
    console.print(Panel(f"[bold yellow]WARN:[/bold yellow] {text}", border_style="yellow", expand=False))


def error(text):
    console.print(Panel(f"[bold red]ERROR:[/bold red] {text}", border_style="red", expand=False))


def banner(title):
    console.print(Panel(
        f"[bold bright_cyan]SHAC // AGENT SWARM INTELLIGENCE ENGINE[/bold bright_cyan]\n"
        f"[bold white]{title}[/bold white]",
        border_style="bright_blue",
        padding=(1, 4),
        expand=False
    ))


def render_nodes_table(active_nodes: list, pending_nodes: list):
    table = Table(title="[bold cyan]Connected Swarm Nodes[/bold cyan]", border_style="blue")
    table.add_column("Node ID", style="magenta", justify="left")
    table.add_column("Network Endpoint", style="white", justify="left")
    table.add_column("State", justify="center")

    for n in pending_nodes:
        table.add_row(n.get("id", "N/A"), n.get("addr", "N/A"), "[yellow bold]PENDING APPROVAL[/yellow bold]")

    for n in active_nodes:
        table.add_row(n.get("id", "N/A"), n.get("addr", "N/A"), "[green bold]ACCEPTED[/green bold]")

    console.print(table)