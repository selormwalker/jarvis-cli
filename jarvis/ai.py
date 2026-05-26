from google import genai
import os
import json
import datetime
from dotenv import load_dotenv

load_dotenv()

# Configure the Gemini API using the new google-genai SDK
api_key = os.getenv("GEMINI_API_KEY")
MODEL_ID = 'gemini-1.5-flash'

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None

def parse_task_nl(user_input: str):
    """
    Uses AI to parse natural language input into structured task data.
    """
    if not client:
        return {"title": user_input, "priority": "medium", "description": ""}

    today = datetime.date.today().isoformat()
    prompt = f"""
    You are a task management assistant. Parse the following user input into a structured JSON object.
    The current date is {today}.
    
    User Input: "{user_input}"
    
    Expected JSON format:
    {{
        "title": "Short descriptive title",
        "priority": "low" | "medium" | "high",
        "due_date": "YYYY-MM-DD" (or null if not mentioned),
        "description": "Any extra details found in the input"
    }}
    
    Return ONLY the raw JSON object.
    """
    
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        text = response.text
        # Cleanup potential markdown formatting
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end])
    except Exception as e:
        print(f"AI Parsing Error: {e}")
        return {"title": user_input, "priority": "medium", "description": ""}

def breakdown_task(task_title: str):
    """
    Uses AI to break down a complex task into smaller actionable subtasks.
    """
    if not client:
        return []

    prompt = f"""
    Break down the following complex task into a list of 3-5 smaller, actionable subtasks.
    Task: "{task_title}"
    
    Return the result as a raw JSON list of strings: ["subtask 1", "subtask 2", ...]
    """
    
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        text = response.text
        start = text.find('[')
        end = text.rfind(']') + 1
        return json.loads(text[start:end])
    except:
        return []

def filter_tasks_nl(query: str, task_list_json: str):
    """
    Uses AI to filter a list of tasks based on a natural language query.
    """
    if not client:
        return []

    prompt = f"""
    You are a task management assistant. Filter the following list of tasks based on the user's query.
    
    Query: "{query}"
    Tasks:
    {task_list_json}
    
    Return the IDs of the matching tasks as a raw JSON list of integers.
    If no tasks match, return an empty list [].
    """
    
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        text = response.text
        start = text.find('[')
        end = text.rfind(']') + 1
        return json.loads(text[start:end])
    except:
        return []
