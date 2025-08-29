import os
import openai
import webbrowser
import pyautogui
import requests
import wolframalpha
import sys
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import subprocess
import json
from typing import Any
from workflow_models import Workflow, Action, ValidationError
from logging_setup import logger

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
wolfram_client = wolframalpha.Client(os.getenv("WOLFRAM_APP_ID"))

# In-memory document for letter writing/editing
current_document = {"content": ""}

def handle_general_chat(prompt):
    logger.info(f"handle_general_chat called with prompt: {prompt!r}")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content
        logger.info(f"handle_general_chat result: {result!r}")
        return result
    except Exception as e:
        logger.error(f"handle_general_chat error: {e}")
        return f"Error: {e}"

def open_application(app_name):
    logger.info(f"open_application called with app_name: {app_name!r}")
    app_map = {
        "chrome": "google-chrome" if os.name != "nt" else "chrome.exe",
        "spotify": "spotify",
        "notepad": "notepad.exe"
    }
    try:
        if os.name == "nt":
            os.startfile(app_map.get(app_name.lower(), app_name))
        else:
            from subprocess import Popen
            Popen(["open" if sys.platform == "darwin" else "xdg-open", app_map.get(app_name.lower(), app_name)])
        logger.info(f"open_application success: {app_name}")
        return f"Opening {app_name}, sir."
    except Exception as e:
        logger.error(f"open_application error: {e}")
        return f"I'm sorry, I couldn't find the application {app_name}. ({e})"

def perform_calculation(query):
    logger.info(f"perform_calculation called with query: {query!r}")
    try:
        res = wolfram_client.query(query)
        result = next(res.results).text
        logger.info(f"perform_calculation result: {result!r}")
        return result
    except Exception as e:
        logger.error(f"perform_calculation error: {e}")
        return f"Sorry, I couldn't compute that. ({e})"

def get_news():
    logger.info("get_news called")
    result = "Headline: Stark Industries Announces Breakthrough in Arc Reactor Technology."
    logger.info(f"get_news result: {result!r}")
    return result

def get_weather(location=""):
    logger.info(f"get_weather called with location: {location!r}")
    result = f"The weather in {location or 'your area'} is currently sunny and 25°C."
    logger.info(f"get_weather result: {result!r}")
    return result

def web_search(query):
    logger.info(f"web_search called with query: {query!r}")
    try:
        webbrowser.open(f"https://www.google.com/search?q={query}")
        logger.info(f"web_search opened browser for: {query!r}")
        return f"Searching the web for '{query}'."
    except Exception as e:
        logger.error(f"web_search error: {e}")
        return f"Error searching the web: {e}"

def system_command(command):
    logger.info(f"system_command called with command: {command!r}")
    return f"System command '{command}' received (not executed for safety)."

# --- Letter/document actions ---
def create_letter(subject, body):
    logger.info(f"create_letter called with subject: {subject!r}, body: {body!r}")
    current_document["content"] = f"Subject: {subject}\n\n{body}"
    logger.info("create_letter updated current_document")
    return "Draft letter created."

def edit_letter(edit_instruction):
    logger.info(f"edit_letter called with edit_instruction: {edit_instruction!r}")
    prompt = f"Current letter:\n{current_document['content']}\n\nEdit instruction: {edit_instruction}\n\nReturn the revised letter."
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        current_document["content"] = response.choices[0].message.content
        logger.info("edit_letter updated current_document")
        return "Letter updated."
    except Exception as e:
        logger.error(f"edit_letter error: {e}")
        return f"Error editing letter: {e}"

def read_letter():
    logger.info("read_letter called")
    result = f"Here is your current letter:\n{current_document['content']}"
    logger.info(f"read_letter result: {result!r}")
    return result

def clear_letter():
    logger.info("clear_letter called")
    current_document["content"] = ""
    logger.info("clear_letter cleared current_document")
    return "Letter cleared."

def send_letter_via_email_macos(to_email, subject=None):
    logger.info(f"send_letter_via_email_macos called with to_email: {to_email!r}, subject: {subject!r}")
    subject = subject or "Letter from JARVIS"
    body = current_document["content"]
    applescript = f'''
    tell application "Mail"
        activate
        set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}\\n\\n", visible:true}}
        tell newMessage
            make new to recipient at end of to recipients with properties {{address:"{to_email}"}}
        end tell
        activate
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", applescript], check=True)
        logger.info(f"send_letter_via_email_macos success for {to_email}")
        return f"Email draft created in Mail.app for {to_email}. Please review and send."
    except Exception as e:
        logger.error(f"send_letter_via_email_macos error: {e}")
        return f"Failed to create email: {e}"

def transcribe_exactly(text):
    logger.info(f"transcribe_exactly called with text: {text!r}")
    return text

def execute_workflow(workflow_json: Any):
    logger.info(f"execute_workflow called with workflow_json: {workflow_json!r}")
    """
    Accepts a workflow as a JSON string or dict, validates and executes each step, and returns a summary.
    """
    try:
        if isinstance(workflow_json, str):
            wf = Workflow.parse_raw(workflow_json)
        else:
            wf = Workflow.parse_obj(workflow_json)
    except ValidationError as e:
        logger.error(f"execute_workflow validation error: {e}")
        return f"Invalid workflow: {e}"

    results = []
    for step in wf.steps:
        action = step.action
        logger.info(f"execute_workflow step: {action}")
        if action == "create_letter":
            results.append(create_letter(step.subject or "", step.body or ""))
        elif action == "edit_letter":
            results.append(edit_letter(step.edit_instruction or ""))
        elif action == "read_letter":
            results.append(read_letter())
        elif action == "clear_letter":
            results.append(clear_letter())
        elif action == "send_letter_via_email_macos":
            results.append(send_letter_via_email_macos(step.to_email or "", step.subject))
        elif action == "web_search":
            results.append(web_search(step.query or ""))
        elif action == "transcribe_exactly":
            results.append(transcribe_exactly(step.text or ""))
        elif action == "perform_calculation":
            results.append(perform_calculation(step.query or ""))
        elif action == "handle_general_chat":
            results.append(handle_general_chat(step.text or ""))
        elif action == "open_application":
            results.append(open_application(step.app_name or ""))
        elif action == "system_command":
            results.append(system_command(step.command or ""))
        elif action == "discuss_programming":
            results.append(handle_general_chat(step.text or ""))
        else:
            logger.warning(f"execute_workflow unknown action: {action}")
            results.append(f"Unknown action: {action}")
    logger.info(f"execute_workflow results: {results!r}")
    return json.dumps({"workflow_results": results}, indent=2)