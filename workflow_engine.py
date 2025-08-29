from workflow_models import Workflow, Action, ValidationError
from typing import Any, Dict, List
import actions
import importlib
from logging_setup import logger
import subprocess
import re
class WorkflowEngine:
    def __init__(self):
        self.last_workflow = None
        self.last_results = None
        logger.info("WorkflowEngine initialized")

    def validate_workflow(self, workflow_json: Any) -> Workflow | None:
        logger.info(f"validate_workflow called with: {workflow_json!r}")
        try:
            if isinstance(workflow_json, str):
                wf = Workflow.parse_raw(workflow_json)
            else:
                wf = Workflow.parse_obj(workflow_json)
            logger.info("validate_workflow success")
            return wf
        except ValidationError as e:
            logger.error(f"validate_workflow error: {e}")
            return None

    def execute_workflow(self, workflow: Workflow, user_utterance: str = "") -> Dict:
        logger.info(f"execute_workflow called with workflow: {workflow}")
        results = []
        for step in workflow.steps:
            action = step.action
            logger.info(f"execute_workflow step: {action}")
            # Dynamically dispatch to actions module
            # Always try to launch apps for open_application or system_command
            auto_tool_match = False
            user_confirmation_needed = False
            if action == "open_application":
                app_name = getattr(step, "app_name", None) or getattr(step, "subject", None) or getattr(step, "body", None)
                if app_name:
                    auto_result = self.auto_tool_handler(app_name.lower(), step)
                    result = auto_result
                    auto_tool_match = True
                    # Only prompt if failed
                    if "Failed to open" in auto_result:
                        user_confirmation_needed = True
            elif action == "system_command":
                command = getattr(step, "command", "")

                match = re.search(r"(open|launch|start)\s+['\"]?([a-zA-Z0-9 ._-]+)['\"]?", command.lower())
                if match:
                    app_name = match.group(2)
                    auto_result = self.auto_tool_handler(app_name, step)
                    result = auto_result
                    auto_tool_match = True
                    if "Failed to open" in auto_result:
                        user_confirmation_needed = True
                else:
                    result = f"System command '{command}' received (not executed for safety)."
                    user_confirmation_needed = True
            if not auto_tool_match and hasattr(actions, action):
                func = getattr(actions, action)
                # Only pass relevant fields that match the function signature
                import inspect
                sig = inspect.signature(func)
                valid_params = {k: v for k, v in step.dict().items() if v is not None and k != "action" and k in sig.parameters}
                extra_params = {k: v for k, v in step.dict().items() if v is not None and k != "action" and k not in sig.parameters}
                if extra_params:
                    logger.warning(f"execute_workflow: extra params for {action} dropped: {extra_params}")
                try:
                    result = func(**valid_params)
                    logger.info(f"execute_workflow {action} result: {result!r}")
                except TypeError as e:
                    # Self-healing: detect missing/invalid arguments and prompt for clarification
                    logger.error(f"execute_workflow argument error in {action}: {e}")
                    missing_args = []
                    import re
                    match = re.findall(r"missing (\d+) required positional argument[s]?: (.+)", str(e))
                    if match:
                        arglist = match[0][1].replace("'", "").replace('"', "").split(", ")
                        missing_args = [arg.strip() for arg in arglist]
                    if missing_args:
                        result = (
                            f"Step '{action}' failed: missing required arguments: {missing_args}. "
                            f"Please provide the missing information to continue."
                        )
                        user_confirmation_needed = True
                    else:
                        result = f"Error executing {action}: {e}"
                        user_confirmation_needed = True
                except Exception as e:
                    logger.error(f"execute_workflow error in {action}: {e}")
                    result = f"Error executing {action}: {e}"
                    user_confirmation_needed = True
            elif not auto_tool_match and not action == "system_command":
                logger.warning(f"execute_workflow unknown action: {action}")
                # Fallback: try to infer app from user utterance
                fallback_result = None
                if user_utterance:
                    for app in ["terminal", "photo booth", "camera", "reminders", "safari", "settings"]:
                        if app in user_utterance.lower():
                            fallback_result = self.auto_tool_handler(app, step)
                            logger.info(f"Fallback auto-tool: tried to open {app} from user utterance.")
                            break
                if fallback_result:
                    result = fallback_result
                else:
                    # Try to auto-generate the missing tool
                    from auto_tool_generation import auto_generate_tool
                    # Use the step's dict to get parameter names
                    params = [k for k, v in step.dict().items() if v is not None and k != "action"]
                    description = f"Auto-generated tool for action '{action}' with parameters {params}."
                    gen_result = auto_generate_tool(action, params, description)
                    logger.info(f"Auto-tool generation result: {gen_result}")
                    # Try to call the new tool
                    importlib.reload(actions)
                    if hasattr(actions, action):
                        func = getattr(actions, action)
                        try:
                            valid_params = {k: v for k, v in step.dict().items() if v is not None and k != "action"}
                            result = func(**valid_params)
                            logger.info(f"Auto-generated tool {action} executed with result: {result!r}")
                        except Exception as e:
                            logger.error(f"Auto-generated tool {action} failed: {e}")
                            result = f"Auto-generated tool {action} failed: {e}"
                    else:
                        result = f"Auto-generated tool {action} could not be loaded."
                user_confirmation_needed = True
            # After each step, check if user confirmation is needed
            if user_confirmation_needed:
                result += (
                    " [Please confirm: Did this step succeed? If not, would you like to retry, clarify, or try an alternative?]"
                )
            results.append({"action": action, "result": result})
        self.last_workflow = workflow
        self.last_results = results
        logger.info(f"execute_workflow results: {results!r}")
        return {"workflow": workflow.dict(), "results": results}

    def auto_tool_handler(self, action, step):
        """
        Attempt to handle unknown actions by opening system apps or providing guidance.
        Adapts to macOS, Windows, or Linux, and asks for clarification if needed.
        """
        import subprocess
        import platform

        os_type = platform.system().lower()
        logger.info(f"auto_tool_handler: Detected OS: {os_type}")

        def try_open(app_name, friendly_name=None):
            try:
                if os_type == "darwin":
                    subprocess.run(["open", "-a", app_name], check=True)
                elif os_type == "windows":
                    subprocess.run(["start", "", app_name], shell=True, check=True)
                elif os_type == "linux":
                    subprocess.run(["xdg-open", app_name], check=True)
                else:
                    return f"Unsupported OS for auto-tool: {os_type}"
                logger.info(f"Auto-tool: Opened {app_name} on {os_type}.")
                return f"Opened {friendly_name or app_name} on your {os_type.capitalize()} system."
            except Exception as e:
                logger.error(f"Auto-tool error opening {app_name}: {e}")
                return f"Failed to open {friendly_name or app_name}: {e}"

        # Camera/Photo Booth
        if "camera" in action or "photo booth" in action or "camera" in (step.subject or "") or "photo booth" in (step.subject or ""):
            if os_type == "darwin":
                return try_open("Photo Booth", "Photo Booth (camera)")
            elif os_type == "windows":
                return try_open("Camera", "Camera app")
            elif os_type == "linux":
                return try_open("cheese", "Cheese (camera app)")
            else:
                return f"Camera opening not supported on your OS: {os_type}"
        # Reminders
        if "reminder" in action or "reminder" in (step.subject or ""):
            if os_type == "darwin":
                return try_open("Reminders", "Reminders app")
            elif os_type == "windows":
                return "Please use the Windows 'Alarms & Clock' or 'Cortana' to set reminders."
            elif os_type == "linux":
                return "Please use your preferred calendar/reminder app on Linux."
        # Safari (web browser)
        if "safari" in action or "browser" in action or "web" in action or "safari" in (step.subject or ""):
            if os_type == "darwin":
                return try_open("Safari", "Safari (web browser)")
            elif os_type == "windows":
                return try_open("chrome", "Chrome browser")
            elif os_type == "linux":
                return try_open("firefox", "Firefox browser")
        # Terminal
        if "terminal" in action or "shell" in action or "terminal" in (step.subject or ""):
            if os_type == "darwin":
                return try_open("Terminal", "Terminal")
            elif os_type == "windows":
                return try_open("cmd", "Command Prompt")
            elif os_type == "linux":
                return try_open("gnome-terminal", "Terminal")
        # System Preferences/Settings
        if "settings" in action or "preferences" in action or "system preferences" in (step.subject or ""):
            if os_type == "darwin":
                return try_open("System Settings", "System Settings")
            elif os_type == "windows":
                return try_open("ms-settings:", "Windows Settings")
            elif os_type == "linux":
                return try_open("gnome-control-center", "Settings")
        # If ambiguous, ask for clarification
        if "open" in action or "launch" in action or "start" in action:
            return (
                "I see you want to open or launch an app, but I need to know the exact app name. "
                "Please specify the application you want to open (e.g., 'open Safari', 'open Terminal', 'open Camera')."
            )
        # Fallback: guidance
        return (
            f"Unknown action: {action}. "
            "JARVIS could not execute this step directly. "
            "If this is a system-level task, please specify your OS and the app you want to use, or ask for a step-by-step guide."
        )

    def handle_missing_info(self, workflow_json: Any) -> List[str]:
        logger.info(f"handle_missing_info called with: {workflow_json!r}")
        # Returns a list of missing required fields for each step
        missing = []
        try:
            Workflow.parse_obj(workflow_json)
        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                missing.append(f"Missing or invalid: {loc} ({err['msg']})")
            logger.warning(f"handle_missing_info found: {missing}")
        return missing

    def discover_and_extend(self, workflow: Workflow, context: Dict) -> Workflow:
        logger.info("discover_and_extend called")
        # Placeholder: In a real agent, use LLM to propose new steps based on context
        # For now, just return the workflow unchanged
        return workflow

# Example usage:
# engine = WorkflowEngine()
# wf = engine.validate_workflow(workflow_json)
# if not wf:
#     missing = engine.handle_missing_info(workflow_json)
#     # Ask user for missing info
# else:
#     result = engine.execute_workflow(wf)