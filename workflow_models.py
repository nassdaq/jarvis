from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Literal, Dict, Any

class Action(BaseModel):
    action: Literal[
        "create_letter",
        "edit_letter",
        "read_letter",
        "clear_letter",
        "send_letter_via_email_macos",
        "web_search",
        "transcribe_exactly",
        "perform_calculation",
        "handle_general_chat",
        "open_application",
        "system_command",
        "discuss_programming"
    ]
    subject: Optional[str] = None
    body: Optional[str] = None
    edit_instruction: Optional[str] = None
    to_email: Optional[str] = None
    query: Optional[str] = None
    text: Optional[str] = None
    command: Optional[str] = None
    app_name: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class Workflow(BaseModel):
    steps: List[Action]
    description: Optional[str] = Field(None, description="A high-level description of the workflow's purpose.")

# Example usage:
# try:
#     wf = Workflow.parse_raw(json_string)
# except ValidationError as e:
#     print("Invalid workflow:", e)