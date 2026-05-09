import typer
from rich.console import Console
from rich.table import Table
from .db import init_db, get_session, Task
from .ai import parse_task_nl, breakdown_task

app = typer.Typer()
console = Console()

@app.callback()
def callback():
    """
    Jarvis: Your AI-Powered Task Manager.
    """
    init_db()

@app.command()
def add(task_input: str, auto_breakdown: bool = typer.Option(False, "--breakdown", "-b", help="Automatically break down complex tasks into subtasks")):
    """
    Add a new task using natural language.
    Example: jarvis add "Buy milk tomorrow high priority"
    """
    with console.status("[bold green]Jarvis is thinking..."):
        parsed = parse_task_nl(task_input)
        
    session = get_session()
    new_task = Task(
        title=parsed.get("title", task_input),
        priority=parsed.get("priority", "medium"),
        description=parsed.get("description", "")
    )
    session.add(new_task)
    session.commit()
    
    console.print(f"[bold green]✔ Main Task Added:[/bold green] {new_task.title} ({new_task.priority} priority)")
    
    if auto_breakdown:
        with console.status("[bold blue]Breaking down task into subtasks..."):
            subtasks = breakdown_task(new_task.title)
            for st_title in subtasks:
                sub_task = Task(title=st_title, parent_id=new_task.id)
                session.add(sub_task)
            session.commit()
            if subtasks:
                console.print(f"[bold blue]↳ Added {len(subtasks)} subtasks automatically.[/bold blue]")

@app.command()
def list():
    """List all tasks and their subtasks."""
    session = get_session()
    tasks = session.query(Task).filter(Task.parent_id == None).all()
    
    if not tasks:
        console.print("[yellow]No tasks found. Try adding one with 'add'.[/yellow]")
        return

    table = Table(title="Jarvis Tasks")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Task", style="cyan")
    table.add_column("Priority", style="magenta")
    table.add_column("Status", style="green")

    for task in tasks:
        table.add_row(str(task.id), task.title, task.priority, task.status)
        # Show subtasks with indentation
        subtasks = session.query(Task).filter(Task.parent_id == task.id).all()
        for sub in subtasks:
            table.add_row(f"  └ {sub.id}", f"[dim]{sub.title}[/dim]", "-", sub.status)

    console.print(table)

@app.command()
def done(task_id: int):
    """Mark a task as completed."""
    session = get_session()
    task = session.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = "done"
        session.commit()
        console.print(f"[bold green]Task {task_id} marked as done.[/bold green]")
    else:
        console.print(f"[bold red]Task {task_id} not found.[/bold red]")

if __name__ == "__main__":
    app()
