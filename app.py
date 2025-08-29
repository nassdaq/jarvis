import streamlit as st
from brain import jarvis_think
import actions
import os

# For voice input/output
import tempfile
from openai import OpenAI

st.title("J.A.R.V.I.S. Protocol - Initialized")
st.markdown("_Welcome, Sir. Let's have a conversation!_")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Conversation State ---
if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": "You are J.A.R.V.I.S., an AI assistant. Respond as a helpful, witty, and loyal digital butler."}
    ]
if "last_response" not in st.session_state:
    st.session_state.last_response = ""

# --- Display Conversation ---
st.subheader("Conversation")
for msg in st.session_state.history[1:]:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    elif msg["role"] == "assistant":
        st.markdown(f"**J.A.R.V.I.S.:** {msg['content']}")

# --- VOICE INPUT ---
st.subheader("🎤 Speak to J.A.R.V.I.S. (Upload WAV/MP3)")
audio_file = st.file_uploader("Upload a short voice message (WAV/MP3)", type=["wav", "mp3"], key="voice")

voice_transcript = ""
if audio_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix="." + audio_file.name.split('.')[-1]) as tmpfile:
        tmpfile.write(audio_file.read())
        tmpfile_path = tmpfile.name

    with st.spinner("Transcribing with Whisper..."):
        with open(tmpfile_path, "rb") as af:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=af
            )
        voice_transcript = transcript.text
        st.success(f"Transcribed: {voice_transcript}")

# --- TEXT INPUT ---
user_input = st.text_input("Or type your message:", value=voice_transcript, key="text")

if st.button("Send", use_container_width=True) or (user_input and st.session_state.last_response != user_input):
    if user_input:
        # Add user message to history
        st.session_state.history.append({"role": "user", "content": user_input})

        # Get assistant response with context
        with st.spinner("J.A.R.V.I.S. is thinking..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.history,
                temperature=0.7
            )
            assistant_reply = response.choices[0].message.content
            st.session_state.history.append({"role": "assistant", "content": assistant_reply})
            st.session_state.last_response = user_input

        # Display and speak response
        st.markdown(f"**J.A.R.V.I.S.:** {assistant_reply}")
        with st.spinner("Synthesizing voice..."):
            tts_response = client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=assistant_reply
            )
            audio_bytes = tts_response.content
            st.audio(audio_bytes, format="audio/mp3")

    # Note: Streamlit does not allow resetting st.session_state["text"] after widget creation.
    # To continue, simply type or upload your next message.

st.markdown("---")
st.caption("You can continue the conversation by uploading another voice message or typing your reply. J.A.R.V.I.S. will remember the context! (Audio will play automatically after each response. If it doesn't, click anywhere on the page to enable audio auto-play.)")