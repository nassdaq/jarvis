import sys
import os
import queue
import sounddevice as sd
import numpy as np
import tempfile
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from PyQt5.QtCore import Qt
from openai import OpenAI
import actions
from dotenv import load_dotenv
import json
from workflow_models import Workflow, ValidationError

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Audio recording parameters
SAMPLE_RATE = 16000
CHANNELS = 1
DURATION = 8  # seconds max per utterance

class JarvisVoice(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS Voice Assistant")
        self.setGeometry(200, 200, 500, 400)
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
        self.audio_queue = queue.Queue()
        self.audio_data = []
        self.conversation = [
            {"role": "system", "content": "You are JARVIS, an AI assistant. Respond as a helpful, witty, and loyal digital butler. Always reply in English, regardless of the user's language. Your name is JARVIS. You can help with any task, including writing, editing, searching, programming, and more. Be fast, concise, and conversational. If a user asks for a multi-step task, output the workflow as a JSON object, then execute it step by step, reporting results. If info is missing, ask for it."}
        ]
        self.button.pressed.connect(self.start_recording)
        self.button.released.connect(self.stop_recording)

    def start_recording(self):
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

    def stop_recording(self):
        self.stream.stop()
        if not self.audio_data:
            self.label.setText("No audio detected. Please try again and speak clearly into the mic.")
            return
        self.label.setText("Processing...")
        audio = np.concatenate(self.audio_data, axis=0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            from scipy.io.wavfile import write
            write(f.name, SAMPLE_RATE, audio)
            wav_path = f.name

        transcript = self.transcribe_audio(wav_path)
        self.text_area.append(f"<b>You:</b> {transcript}")
        self.conversation.append({"role": "user", "content": transcript})

        # Intent detection and action routing
        response_text = self.route_intent(transcript)
        self.text_area.append(f"<b>JARVIS:</b> {response_text}")
        self.conversation.append({"role": "assistant", "content": response_text})

        # Speak response
        self.speak_response(response_text)
        self.label.setText("Press and hold the button, speak, then release.")

    def transcribe_audio(self, wav_path):
        with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        return transcript.text

    def route_intent(self, user_text):
        text = user_text.lower()
        # Dictation mode
        if "dictate exactly" in text or "transcribe exactly" in text:
            return actions.transcribe_exactly(user_text)
        # Letter/document actions
        if "write a letter" in text or "create a letter" in text:
            subject = "Letter"
            body = user_text.split("letter", 1)[-1].strip() or "This is a draft letter."
            return actions.create_letter(subject, body)
        elif "edit the letter" in text or "change the letter" in text or "update the letter" in text:
            edit_instruction = user_text
            return actions.edit_letter(edit_instruction)
        elif "read the letter" in text or "show the letter" in text:
            return actions.read_letter()
        elif "clear the letter" in text or "delete the letter" in text:
            return actions.clear_letter()
        elif "send the letter" in text or "email the letter" in text:
            return actions.send_letter_via_email_macos("your@email.com")
        # Web search
        elif "search online" in text or "google" in text or "search for" in text:
            query = user_text.split("search", 1)[-1].strip() or user_text
            return actions.web_search(query)
        # Programming discussion
        elif "code" in text or "programming" in text or "python" in text or "javascript" in text:
            return actions.discuss_programming(user_text)
        # Calculation
        elif any(word in text for word in ["calculate", "what is", "how much", "square root", "plus", "minus", "times", "divided by"]):
            return actions.perform_calculation(user_text)
        # Workflow execution (JSON)
        elif "workflow" in text or "do these steps" in text or "multi-step" in text:
            workflow_json = self.ask_for_workflow_json(user_text)
            self.text_area.append(f"<b>Workflow JSON:</b>\n{workflow_json}")
            # Validate and execute workflow using Pydantic
            try:
                wf = Workflow.parse_raw(workflow_json)
            except ValidationError as e:
                return f"Invalid workflow: {e}"
            return actions.execute_workflow(workflow_json)
        # General chat
        else:
            return actions.handle_general_chat(user_text)

    def ask_for_workflow_json(self, user_text):
        prompt = f"User request: {user_text}\n\nOutput a JSON object describing the workflow steps needed to accomplish this task. Each step should have an 'action' and relevant parameters. Only output the JSON. Use this JSON schema:\n{Workflow.schema_json(indent=2)}"
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    def speak_response(self, text):
        tts_response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text
        )
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(tts_response.content)
            mp3_path = f.name
        subprocess.run(["afplay", mp3_path])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JarvisVoice()
    window.show()
    sys.exit(app.exec_())