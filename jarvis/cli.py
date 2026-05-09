import typer
import json
from rich.console import Console
from rich.table import Table
from datetime import datetime
from .db import init_db, get_session, Task
from .ai import parse_task_nl, breakdown_task, filter_tasks_nl

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
    Example: jarvis add "Prepare for meeting with team tomorrow morning high priority"
    """
    with console.status("[bold green]Jarvis is processing your request..."):
        parsed = parse_task_nl(task_input)
        
    session = get_session()
    
    # Handle due_date parsing
    due_date_obj = None
    if parsed.get("due_date"):
        try:
            due_date_obj = datetime.strptime(parsed["due_date"], "%Y-%m-%d")
        except:
            pass

    new_task = Task(
        title=parsed.get("title", task_input),
        priority=parsed.get("priority", "medium"),
        description=parsed.get("description", ""),
        due_date=due_date_obj
    )
    session.add(new_task)
    session.commit()
    
    date_str = f" [dim](Due: {parsed['due_date']})[/dim]" if parsed.get("due_date") else ""
    console.print(f"[bold green]✔ Added:[/bold green] {new_task.title} [{new_task.priority.upper()}]{date_str}")
    
    if auto_breakdown:
        with console.status("[bold blue]Generating subtasks..."):
            subtasks = breakdown_task(new_task.title)
            for st_title in subtasks:
                sub_task = Task(title=st_title, parent_id=new_task.id)
                session.add(sub_task)
            session.commit()
            if subtasks:
                console.print(f"[bold blue]↳ Intelligently generated {len(subtasks)} subtasks.[/bold blue]")

@app.command()
def list():
    """List all tasks and their subtasks."""
    session = get_session()
    tasks = session.query(Task).filter(Task.parent_id == None).all()
    
    if not tasks:
        console.print("[yellow]Your task list is empty. Jarvis is ready for new tasks![/yellow]")
        return

    table = Table(title="Jarvis Executive Task Overview", show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Task", style="white")
    table.add_column("Priority", justify="center")
    table.add_column("Due Date", justify="center", style="dim")
    table.add_column("Status", justify="right")

    for task in tasks:
        p_style = "red" if task.priority == "high" else "yellow" if task.priority == "medium" else "green"
        due_str = task.due_date.strftime("%Y-%m-%d") if task.due_date else "-"
        status_str = "[bold green]DONE[/bold green]" if task.status == "done" else "[yellow]TODO[/yellow]"
        
        table.add_row(str(task.id), task.title, f"[{p_style}]{task.priority.upper()}[/{p_style}]", due_str, status_str)
        
        # Show subtasks
        subtasks = session.query(Task).filter(Task.parent_id == task.id).all()
        for sub in subtasks:
            sub_status = "✓" if sub.status == "done" else "○"
            table.add_row(f"  {sub.id}", f"  [dim]└ {sub.title}[/dim]", "-", "-", f"[dim]{sub_status}[/dim]")

    console.print(table)

@app.command()
def done(task_id: int):
    """Mark a task as completed."""
    session = get_session()
    task = session.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = "done"
        session.commit()
        console.print(f"[bold green]✔ Task {task_id} completed. Well done![/bold green]")
    else:
        console.print(f"[bold red]✘ Task {task_id} not found.[/bold red]")

@app.command()
def query(text: str):
    """
    Search and filter tasks using natural language.
    Example: jarvis query "What are my high priority tasks?"
    """
    session = get_session()
    all_tasks = session.query(Task).all()
    
    # Convert tasks to simple JSON for AI processing
    task_data = []
    for t in all_tasks:
        task_data.append({
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "due_date": t.due_date.strftime("%Y-%m-%d") if t.due_date else "none",
            "status": t.status
        })
    
    with console.status("[bold green]Jarvis is searching..."):
        matching_ids = filter_tasks_nl(text, json.dumps(task_data))
    
    if not matching_ids:
        console.print("[yellow]No tasks found matching your query.[/yellow]")
        return

    table = Table(title=f"Search Results for: {text}", show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Task", style="white")
    table.add_column("Priority", justify="center")
    table.add_column("Due Date", justify="center", style="dim")
    table.add_column("Status", justify="right")

    for t in all_tasks:
        if t.id in matching_ids:
            p_style = "red" if t.priority == "high" else "yellow" if t.priority == "medium" else "green"
            due_str = t.due_date.strftime("%Y-%m-%d") if t.due_date else "-"
            status_str = "[bold green]DONE[/bold green]" if t.status == "done" else "[yellow]TODO[/yellow]"
            table.add_row(str(t.id), t.title, f"[{p_style}]{t.priority.upper()}[/{p_style}]", due_str, status_str)

    console.print(table)

@app.command()
def clear():
    """Clear all completed tasks."""
    session = get_session()
    deleted = session.query(Task).filter(Task.status == "done").delete()
    session.commit()
    console.print(f"[bold yellow]Purged {deleted} completed tasks from database.[/bold yellow]")

if __name__ == "__main__":
    app()
