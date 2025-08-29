import importlib
import os
from logging_setup import logger
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

ACTIONS_FILE = "actions.py"

def auto_generate_tool(action_name, params, description=""):
    """
    Use LLM to generate a Python function for the missing tool and append it to actions.py.
    """
    logger.info(f"Auto-generating tool: {action_name} with params {params}")
    param_str = ", ".join(params)
    docstring = f'"""{description or f"Auto-generated tool for {action_name}."}"""'
    prompt = (
        f"Write a Python function named '{action_name}' that takes parameters: {param_str}. "
        f"{description or 'The function should perform the intended action safely and return a status message.'} "
        "Do not use any destructive operations. Return a string describing the result."
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a Python code generator for an AI agent. Only output the function code."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    code = response.choices[0].message.content.strip()
    # Ensure only the function code is extracted
    if code.startswith("```"):
        code = code.split("```")[1]
        if code.startswith("python"):
            code = code[len("python"):].strip()
    # Append to actions.py
    with open(ACTIONS_FILE, "a", encoding="utf-8") as f:
        f.write("\n\n" + code + "\n")
    logger.info(f"Appended new tool to {ACTIONS_FILE}: {action_name}")
    # Reload actions module
    import actions
    importlib.reload(actions)
    return f"Auto-generated and loaded new tool: {action_name}"