import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configure the Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

def parse_task_nl(user_input: str):
    """
    Uses AI to parse natural language input into structured task data.
    """
    if not model:
        return {"title": user_input, "priority": "medium", "description": ""}

    prompt = f"""
    Parse the following task description into a JSON object with 'title', 'priority' (low, medium, high), and 'description'.
    Task: "{user_input}"
    JSON:
    """
    
    response = model.generate_content(prompt)
    try:
        # Simple extraction of JSON from response
        text = response.text
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end])
    except:
        return {"title": user_input, "priority": "medium", "description": ""}

def breakdown_task(task_title: str):
    """
    Uses AI to break down a complex task into smaller actionable subtasks.
    """
    if not model:
        return []

    prompt = f"""
    Break down the following complex task into 3-5 smaller, actionable subtasks.
    Task: "{task_title}"
    Return the result as a JSON list of strings.
    JSON:
    """
    
    response = model.generate_content(prompt)
    try:
        text = response.text
        start = text.find('[')
        end = text.rfind(']') + 1
        return json.loads(text[start:end])
    except:
        return []
