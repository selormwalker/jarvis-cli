import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jarvis.db import Base, Task

@pytest.fixture
def session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def test_create_task(session):
    task = Task(title="Test Task", priority="high")
    session.add(task)
    session.commit()
    
    saved_task = session.query(Task).first()
    assert saved_task.title == "Test Task"
    assert saved_task.priority == "high"
    assert saved_task.status == "todo"

def test_subtasks(session):
    parent = Task(title="Parent Task")
    session.add(parent)
    session.commit()
    
    child = Task(title="Child Task", parent_id=parent.id)
    session.add(child)
    session.commit()
    
    # Reload parent
    parent = session.query(Task).filter_by(title="Parent Task").first()
    # Let's see if subtasks relationship works
    # The current definition is suspicious: backref=ForeignKey('tasks.id')
    try:
        assert len(parent.subtasks) == 1
        assert parent.subtasks[0].title == "Child Task"
    except Exception as e:
        pytest.fail(f"Subtask relationship failed: {e}")
