from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    priority = Column(String, default="medium") # low, medium, high
    status = Column(String, default="todo") # todo, in_progress, done
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    parent_id = Column(Integer, ForeignKey('tasks.id'))
    subtasks = relationship("Task", backref=ForeignKey('tasks.id'), remote_side=[id])

engine = create_engine('sqlite:///jarvis.db')
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return Session()
