import typer
import json
import os
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
        tags=parsed.get("tags", ""),
        due_date=due_date_obj
    )
    session.add(new_task)
    session.commit()
    
    date_str = f" [dim](Due: {parsed['due_date']})[/dim]" if parsed.get("due_date") else ""
    tag_str = f" [cyan]#{parsed['tags'].replace(',', ' #')}[/cyan]" if parsed.get("tags") else ""
    console.print(f"[bold green]✔ Added:[/bold green] {new_task.title} [{new_task.priority.upper()}]{date_str}{tag_str}")
    
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
    table.add_column("Tags", style="cyan")
    table.add_column("Due Date", justify="center", style="dim")
    table.add_column("Status", justify="right")

    for task in tasks:
        # Show subtasks and calculate progress
        subtasks = session.query(Task).filter(Task.parent_id == task.id).all()
        progress = ""
        if subtasks:
            done_count = sum(1 for s in subtasks if s.status == "done")
            progress = f" [dim]({done_count}/{len(subtasks)})[/dim]"

        p_style = "red" if task.priority == "high" else "yellow" if task.priority == "medium" else "green"
        due_str = task.due_date.strftime("%Y-%m-%d") if task.due_date else "-"
        status_str = "[bold green]DONE[/bold green]" if task.status == "done" else "[yellow]TODO[/yellow]"
        tags_str = task.tags.replace(",", " ") if task.tags else "-"
        
        table.add_row(str(task.id), task.title + progress, f"[{p_style}]{task.priority.upper()}[/{p_style}]", tags_str, due_str, status_str)
        
        for sub in subtasks:
            sub_status = "✓" if sub.status == "done" else "○"
            table.add_row(f"  {sub.id}", f"  [dim]└ {sub.title}[/dim]", "-", "-", "-", f"[dim]{sub_status}[/dim]")

    console.print(table)

@app.command()
def export(file_path: str = "tasks_export.json"):
    """Export all tasks to a JSON file."""
    session = get_session()
    tasks = session.query(Task).all()
    data = []
    for t in tasks:
        data.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "status": t.status,
            "tags": t.tags,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "parent_id": t.parent_id
        })
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
    console.print(f"[bold green]✔ Exported {len(data)} tasks to {file_path}[/bold green]")

@app.command()
def import_tasks(file_path: str):
    """Import tasks from a JSON file."""
    if not os.path.exists(file_path):
        console.print(f"[bold red]✘ File {file_path} not found.[/bold red]")
        return
        
    with open(file_path, "r") as f:
        data = json.load(f)
        
    session = get_session()
    for item in data:
        due_date = datetime.fromisoformat(item["due_date"]) if item.get("due_date") else None
        new_task = Task(
            title=item["title"],
            description=item.get("description"),
            priority=item.get("priority", "medium"),
            status=item.get("status", "todo"),
            tags=item.get("tags"),
            due_date=due_date,
            parent_id=item.get("parent_id")
        )
        session.add(new_task)
    session.commit()
    console.print(f"[bold green]✔ Imported {len(data)} tasks from {file_path}[/bold green]")

@app.command()
def shell():
    """Enter interactive mode."""
    console.print("[bold blue]Entering Jarvis Interactive Shell. Type 'exit' or 'quit' to leave.[/bold blue]")
    while True:
        cmd = console.input("[bold green]jarvis> [/bold green]").strip()
        if cmd.lower() in ["exit", "quit"]:
            break
        if not cmd:
            continue
        
        # Simple parsing for interactive shell
        import shlex
        try:
            args = shlex.split(cmd)
            app(args)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def remind():
    """Check for tasks due soon and send notifications."""
    try:
        from plyer import notification
    except ImportError:
        console.print("[yellow]Reminder feature requires 'plyer'. Installing...[/yellow]")
        import subprocess
        subprocess.run(["pip", "install", "plyer"], check=True)
        from plyer import notification

    session = get_session()
    now = datetime.now()
    # Find tasks due in the next 24 hours that haven't had a reminder sent
    tasks = session.query(Task).filter(
        Task.status != "done",
        Task.due_date != None,
        Task.reminder_sent == False
    ).all()
    
    count = 0
    for task in tasks:
        diff = task.due_date - now
        if 0 <= diff.total_seconds() <= 86400: # 24 hours
            notification.notify(
                title=f"Jarvis Reminder: {task.title}",
                message=f"Priority: {task.priority.upper()}\nDue: {task.due_date.strftime('%Y-%m-%d %H:%M')}",
                app_name="Jarvis CLI"
            )
            task.reminder_sent = True
            count += 1
    
    session.commit()
    if count > 0:
        console.print(f"[bold green]✔ Sent {count} notifications.[/bold green]")
    else:
        console.print("[dim]No urgent reminders to send.[/dim]")

@app.command()
def done(task_id: int, recursive: bool = typer.Option(False, "--recursive", "-r", help="Mark all subtasks as done")):
    """Mark a task as completed."""
    session = get_session()
    task = session.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = "done"
        if recursive:
            session.query(Task).filter(Task.parent_id == task_id).update({"status": "done"})
        session.commit()
        console.print(f"[bold green]✔ Task {task_id} completed. Well done![/bold green]")
    else:
        console.print(f"[bold red]✘ Task {task_id} not found.[/bold red]")

@app.command()
def delete(task_id: int):
    """Delete a task and its subtasks."""
    session = get_session()
    task = session.query(Task).filter(Task.id == task_id).first()
    if task:
        # Also delete subtasks
        session.query(Task).filter(Task.parent_id == task_id).delete()
        session.delete(task)
        session.commit()
        console.print(f"[bold red]✘ Task {task_id} and its subtasks deleted.[/bold red]")
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
