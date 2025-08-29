import datetime
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic import BaseModel, Field
from workflow_models import Workflow
import os
import subprocess
from dotenv import load_dotenv
load_dotenv()
from logging_setup import logger


# --- System Prompt: Proactive, Context-Aware, Workflow-Driven ---
JARVIS_SYSTEM_PROMPT = """
You are Jarvis, an advanced AI agent. You proactively help the user, anticipate needs, and can autonomously create and execute multi-step workflows. 
- Always output workflows as structured JSON (validated with Pydantic models) for all multi-step tasks.
- If information is missing or ambiguous, ask concise clarifying questions.
- You can use tools, run commands, send emails, and manage files.
- You maintain and summarize conversation and workflow history, and use it to inform your actions.
- You can discover and propose new subtasks, orchestrate their execution, and report results in a concise, non-chatty, structured manner.
- For every workflow, output the JSON, then execute and report results as JSON.
"""

# --- Agent Output Model ---
class JarvisResponse(BaseModel):
    response: str = Field(description="Jarvis's spoken response")
    workflow: Workflow | None = Field(default=None, description="Workflow to execute, if any")
    result: dict | None = Field(default=None, description="Result of workflow execution, if any")
    ask: str | None = Field(default=None, description="Clarifying question if info is missing")

# --- Agent Dependencies ---
class JarvisDeps:
    def __init__(self, user_name, email_address=None):
        self.user_name = user_name
        self.email_address = email_address
        self.current_time = datetime.datetime.now

# --- Agent Setup ---
logger.info("Instantiating JARVIS agent")
jarvis = Agent(
    model="gpt-4o",
    deps_type=JarvisDeps,
    output_type=JarvisResponse,
    system_prompt=JARVIS_SYSTEM_PROMPT
)
logger.info("JARVIS agent instantiated")

# --- Dynamic Context Injection ---
@jarvis.system_prompt
def add_context(ctx: RunContext[JarvisDeps]) -> str:
    return f"""
    Current user: {ctx.deps.user_name}
    Current time: {ctx.deps.current_time()}
    Mission: Proactively assist, plan, and execute user tasks as workflows.
    """

# --- Example: Tool Registration (see actions.py for actual implementations) ---


@jarvis.tool
def send_email(
    ctx: RunContext[JarvisDeps],
    recipient: str,
    subject: str,
    body: str,
    html: str = None,
    attachments: list = None
) -> str:
    """
    Send an email using AppleScript and Mail.app on macOS.

    Args:
        ctx: Pydantic AI context (injected automatically).
        recipient: Email address of the recipient.
        subject: Subject line of the email.
        body: Plain text body of the email.
        html: Optional HTML content for the email.
        attachments: Optional list of file paths to attach.

    Returns:
        Status message indicating success or failure.
    """
    logger.info(f"send_email tool called: recipient={recipient}, subject={subject}, attachments={attachments}")
    applescript = f'''
    tell application "Mail"
        activate
        set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}\\n\\n", visible:true}}
        tell newMessage
            make new to recipient at end of to recipients with properties {{address:"{recipient}"}}
    '''
    if attachments:
        for path in attachments:
            applescript += f'''
            try
                make new attachment with properties {{file name:"{path}"}} at after the last paragraph
            end try
            '''
    applescript += '''
        end tell
        activate
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", applescript], check=True)
        logger.info(f"send_email success for {recipient}")
        return f"Email draft created in Mail.app for {recipient}. Please review and send."
    except Exception as e:
        logger.error(f"send_email error: {e}")
        return f"Failed to create email: {e}"

@jarvis.tool
def create_letter(
    ctx: RunContext[JarvisDeps],
    subject: str,
    body: str
) -> str:
    """
    Create a letter as a .txt file on the Desktop (macOS).

    Args:
        ctx: Pydantic AI context (injected automatically).
        subject: Subject of the letter.
        body: Body content of the letter.

    Returns:
        Status message indicating success or failure.
    """
    logger.info(f"create_letter tool called: subject={subject}")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    filename = f"Letter_{subject.replace(' ', '_')}.txt"
    path = os.path.join(desktop, filename)
    try:
        with open(path, "w") as f:
            f.write(f"Subject: {subject}\n\n{body}")
        logger.info(f"create_letter success: {path}")
        return f"Letter created at {path}"
    except Exception as e:
        logger.error(f"create_letter error: {e}")
        return f"Failed to create letter: {e}"