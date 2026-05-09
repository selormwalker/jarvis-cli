import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def add(task: str):
    """Add a new task using natural language."""
    console.print(f"[bold green]Added task:[/bold green] {task}")

@app.command()
def list():
    """List all tasks."""
    console.print("[bold blue]Task List:[/bold blue]")
    console.print("1. Implement AI parsing")

if __name__ == "__main__":
    app()
