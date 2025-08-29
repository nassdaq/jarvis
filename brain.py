from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def jarvis_think(user_command):
    """
    Uses GPT to classify the user's intent and generate a JSON command for J.A.R.V.I.S. to execute.
    """
    system_prompt = '''
You are J.A.R.V.I.S., an AI assistant. Analyze the user's command and output a JSON object with two fields:
- "intent": The category of the command. Choose from: ["general_chat", "open_application", "web_search", "system_command", "calculation", "get_news", "get_weather"].
- "action": The specific action to take. For example, if the intent is "open_application", the action should be the app name like "chrome", "spotify", or "notepad".

Example Input: "Open Chrome and find me recipes for pizza"
Example Output: {"intent": "open_application", "action": "chrome"}

Example Input: "What's the square root of 225?"
Example Output: {"intent": "calculation", "action": "square root of 225"}
    '''

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_command}
        ],
        temperature=0
    )
    # Parse the JSON response from GPT
    content = response.choices[0].message.content
    return json.loads(content)