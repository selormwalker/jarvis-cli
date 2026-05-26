import pytest
from typer.testing import CliRunner
from jarvis.cli import app
from jarvis.db import Base, Task, engine
from unittest.mock import patch, MagicMock
import json

runner = CliRunner()

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def test_add_task_cli():
    with patch('jarvis.cli.parse_task_nl') as mock_parse:
        mock_parse.return_value = {
            "title": "Cli Task",
            "priority": "high",
            "due_date": "2026-06-01",
            "description": "Desc"
        }
        result = runner.invoke(app, ["add", "some input"])
        assert result.exit_code == 0
        assert "✔ Added: Cli Task [HIGH]" in result.stdout

def test_list_tasks_cli():
    # Pre-populate
    from jarvis.db import get_session
    session = get_session()
    task = Task(title="List Test", priority="low")
    session.add(task)
    session.commit()
    
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "List Test" in result.stdout
    assert "LOW" in result.stdout

def test_done_recursive_cli():
    from jarvis.db import get_session
    session = get_session()
    parent = Task(title="Parent")
    session.add(parent)
    session.commit()
    
    child = Task(title="Child", parent_id=parent.id)
    session.add(child)
    session.commit()
    
    result = runner.invoke(app, ["done", str(parent.id), "--recursive"])
    assert result.exit_code == 0
    
    session.expire_all()
    assert session.query(Task).filter_by(id=child.id).first().status == "done"

def test_delete_task_cli():
    from jarvis.db import get_session
    session = get_session()
    task = Task(title="Delete Me")
    session.add(task)
    session.commit()
    task_id = task.id
    
    result = runner.invoke(app, ["delete", str(task_id)])
    assert result.exit_code == 0
    assert f"Task {task_id} and its subtasks deleted" in result.stdout
    
    assert session.query(Task).filter_by(id=task_id).first() is None
