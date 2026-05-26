import pytest
from unittest.mock import MagicMock, patch
import json
from jarvis.ai import parse_task_nl, breakdown_task, filter_tasks_nl

@pytest.fixture
def mock_client():
    with patch('jarvis.ai.client') as mock:
        yield mock

def test_parse_task_nl_success(mock_client):
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "title": "Buy milk",
        "priority": "low",
        "due_date": "2026-06-01",
        "description": "Get organic milk"
    })
    mock_client.models.generate_content.return_value = mock_response
    
    result = parse_task_nl("Buy milk tomorrow priority low")
    
    assert result["title"] == "Buy milk"
    assert result["priority"] == "low"
    assert result["due_date"] == "2026-06-01"

def test_parse_task_nl_failure(mock_client):
    mock_client.models.generate_content.side_effect = Exception("API Error")
    
    result = parse_task_nl("Any task")
    
    # Should fallback to basic info
    assert result["title"] == "Any task"
    assert result["priority"] == "medium"

def test_breakdown_task(mock_client):
    mock_response = MagicMock()
    mock_response.text = '["Step 1", "Step 2"]'
    mock_client.models.generate_content.return_value = mock_response
    
    result = breakdown_task("A complex task")
    
    assert len(result) == 2
    assert result[0] == "Step 1"

def test_filter_tasks_nl(mock_client):
    mock_response = MagicMock()
    mock_response.text = '[1, 3]'
    mock_client.models.generate_content.return_value = mock_response
    
    result = filter_tasks_nl("high priority tasks", "[]")
    
    assert result == [1, 3]
