import sys
import os
import queue
import sounddevice as sd
import numpy as np
import tempfile
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt5.QtCore import Qt
from dotenv import load_dotenv
from openai import OpenAI
from logging_setup import logger

from jarvis_agent import jarvis, JarvisDeps
from workflow_engine import WorkflowEngine
from workflow_models import Workflow, ValidationError
from memory_store import MemoryStore

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

SAMPLE_RATE = 16000
CHANNELS = 1

class JarvisMainUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS Unified Assistant")
        self.setGeometry(200, 200, 600, 500)
        self.layout = QVBoxLayout()
        self.label = QLabel("Press and hold the button, speak, then release.")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.layout.addWidget(self.text_area)
        self.button = QPushButton("🎤 Hold to Talk")
        self.button.setCheckable(True)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)
        self.audio_data = []
        self.agent = jarvis
        self.workflow_engine = WorkflowEngine()
        self.deps = JarvisDeps(user_name="User")  # Extend as needed
        self.memory = MemoryStore()
        self.button.pressed.connect(self.start_recording)
        self.button.released.connect(self.stop_recording)
        logger.info("JarvisMainUI initialized")

    def start_recording(self):
        logger.info("start_recording called")
        self.label.setText("Listening...")
        self.audio_data = []
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            callback=self.audio_callback
        )
        self.stream.start()

    def audio_callback(self, indata, frames, time, status):
        self.audio_data.append(indata.copy())
        # Optionally log audio callback events if needed

    def stop_recording(self):
        logger.info("stop_recording called")
        self.stream.stop()
        if not self.audio_data:
            logger.warning("No audio detected in stop_recording")
            self.label.setText("No audio detected. Please try again and speak clearly into the mic.")
            return
        self.label.setText("Processing...")
        audio = np.concatenate(self.audio_data, axis=0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            from scipy.io.wavfile import write
            write(f.name, SAMPLE_RATE, audio)
            wav_path = f.name

        transcript = self.transcribe_audio(wav_path)
        logger.info(f"Transcribed audio: {transcript!r}")
        self.text_area.append(f"<b>You:</b> {transcript}")
        self.memory.add("user", transcript)

        # Retrieve recent memory and inject as context
        recent_memory = self.memory.summarize(limit=20)
        logger.info(f"Injecting memory into agent context: {recent_memory!r}")

        # Route through the agent for workflow planning/execution
        # Add memory as a prefix to the user message for context
        full_prompt = f"Recent memory:\n{recent_memory}\n\nUser: {transcript}"
        agent_result = self.agent.run_sync(full_prompt, deps=self.deps)
        logger.info(f"Agent result: {agent_result}")
        output = agent_result.output
        if output and output.ask:
            logger.info(f"JARVIS clarification: {output.ask}")
            self.text_area.append(f"<b>JARVIS (clarification):</b> {output.ask}")
            self.memory.add("assistant", output.ask, meta={"type": "clarification"})
            self.speak_response(output.ask)
        if output and output.workflow:
            logger.info(f"JARVIS workflow: {output.workflow.model_dump_json(indent=2)}")
            self.text_area.append(f"<b>Workflow JSON:</b>\n{output.workflow.model_dump_json(indent=2)}")
            self.memory.add("assistant", output.workflow.model_dump_json(), meta={"type": "workflow"})
            # Validate and execute workflow
            wf = self.workflow_engine.validate_workflow(output.workflow.dict())
            if not wf:
                missing = self.workflow_engine.handle_missing_info(output.workflow.dict())
                logger.warning(f"Missing workflow info: {missing}")
                self.text_area.append(f"<b>Missing info:</b> {missing}")
                self.memory.add("assistant", f"Missing info: {missing}", meta={"type": "missing_info"})
                self.speak_response("I need more information to proceed.")
            else:
                result = self.workflow_engine.execute_workflow(wf)
                logger.info(f"Workflow execution result: {result}")
                self.text_area.append(f"<b>Workflow Results:</b>\n{result}")
                self.memory.add("assistant", str(result), meta={"type": "workflow_result"})
                self.speak_response(str(result))
        if output and output.response:
            logger.info(f"JARVIS response: {output.response}")
            self.text_area.append(f"<b>JARVIS:</b> {output.response}")
            self.memory.add("assistant", output.response)
            self.speak_response(output.response)

        self.label.setText("Press and hold the button, speak, then release.")

    def transcribe_audio(self, wav_path):
        logger.info(f"transcribe_audio called with wav_path: {wav_path}")
        with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        logger.info(f"transcribe_audio result: {transcript.text!r}")
        return transcript.text

    def speak_response(self, text):
        logger.info(f"speak_response called with text: {text!r}")
        tts_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text
        )
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(tts_response.content)
            mp3_path = f.name
        logger.info(f"speak_response playing audio: {mp3_path}")
        subprocess.run(["afplay", mp3_path])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JarvisMainUI()
    window.show()
    sys.exit(app.exec_())