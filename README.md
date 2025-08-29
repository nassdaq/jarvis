# J.A.R.V.I.S. Lite

A hackathon-style, modular AI assistant inspired by Tony Stark's J.A.R.V.I.S. — with voice and text interface, intent classification, and action execution.

---

## Features

- **Text and Voice Input:** Type or upload a voice command (WAV/MP3).
- **Intent Classification:** Uses OpenAI GPT-4o to understand your request.
- **Action Execution:** Handles chat, app launching, calculations, news, weather, and more.
- **Voice Output:** J.A.R.V.I.S. responds with synthesized speech (OpenAI TTS).
- **Extensible:** Add new actions easily in `actions.py`.

---

## Setup

1. **Clone or copy the project files into your workspace directory.**

2. **Install dependencies:**
   ```bash
   pip install streamlit openai pyautogui requests wolframalpha python-dotenv sounddevice scipy pydub
   ```

3. **Get your API keys:**
   - [OpenAI API Key](https://platform.openai.com/account/api-keys)
   - [WolframAlpha App ID](https://developer.wolframalpha.com/portal/myapps/)

4. **Create a `.env` file in the project root:**
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   WOLFRAM_APP_ID=your-wolframalpha-app-id-here
   ```

---

## Usage

1. **Start the app:**
   ```bash
   streamlit run app.py
   ```

2. **In your browser:**
   - Type a command (e.g., "What's the weather in Malibu?")
   - Or upload a short WAV/MP3 file with your voice command.

3. **J.A.R.V.I.S. will:**
   - Transcribe voice (if provided) using Whisper.
   - Classify your intent and execute the action.
   - Respond in text and with synthesized voice (TTS).

---

## Notes

- **Voice Input:** For best results, upload clear, short WAV or MP3 files.
- **Voice Output:** Uses OpenAI TTS (model: `tts-1`, voice: `onyx`).
- **App Launching:** The `open_application` function is a stub; extend it for your OS/apps.
- **Extending:** Add new actions in `actions.py` and update intent categories in `brain.py`.

---

## Example Commands

- "Open Chrome"
- "What's the square root of 225?"
- "Tell me the latest news."
- "What's the weather in Malibu?"
- "Say hello, J.A.R.V.I.S."

---

## Troubleshooting

- If you see errors about OpenAI API usage, ensure you have the latest `openai` Python package and correct API keys.
- For audio issues, ensure your browser supports audio playback and your files are in WAV/MP3 format.

---

## License

MIT License. For educational and personal use.