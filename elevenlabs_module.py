# elevenlabs_module.py
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import tempfile
import streamlit as st

# --- Voice Configuration ---
# TODO: Replace these placeholder IDs with your actual ElevenLabs Voice IDs.
# You can find Voice IDs in your VoiceLab on the ElevenLabs website.
# They look like this: '21m00Tcm4TlvDq8ikWAM'
CHARACTER_VOICE_MAP = {
    'a': '0rOfEdoZRnNF0sbnFR5B', # Artie
    'b': 'PdXvwvHc8PDiZVI7iUTD', # B00L
    'c': 'Px4v5nXnQ6QfAZufyV2u', # Cling
    'd': 'YBrpT1nAa8RMDOHHRgF7', # Dusty
    'default': '4YYIPFl9wE5c4L2eu2Gb'  # Burt Reynolds
}

def get_elevenlabs_client():
    """Initializes and returns the ElevenLabs client."""
    try:
        api_key = st.secrets.get("ELEVENLABS_API_KEY")
        if not api_key:
            return None, "ELEVENLABS_API_KEY not found in st.secrets."
        client = ElevenLabs(api_key=api_key)
        return client, None
    except Exception as e:
        return None, f"Failed to initialize ElevenLabs client: {e}"

def generate_speech_for_line(character_id, text):
    """
    Generates an audio file from text using ElevenLabs TTS.
    This function has the same signature as the old OpenAI TTS function for easy swapping.
    """
    if not text or not text.strip():
        return None, None # Represents a pause for lines with no dialogue

    client, error = get_elevenlabs_client()
    if error:
        return None, error

    voice_id = CHARACTER_VOICE_MAP.get(character_id.lower(), CHARACTER_VOICE_MAP['default'])

    if "placeholder" in voice_id:
        return None, f"Character '{character_id}' is using a placeholder Voice ID. Please update it in elevenlabs_module.py."

    try:
        # Generate the audio bytes
        audio_bytes = client.generate(
            text=text,
            voice=voice_id,
            model="eleven_multilingual_v2" # A good general-purpose model
        )

        # Create a temporary file to save the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
            save(audio_bytes, temp_audio_file.name)
            temp_audio_path = temp_audio_file.name
        
        print(f"Generated ElevenLabs audio for '{text}' at: {temp_audio_path}")
        return temp_audio_path, None

    except Exception as e:
        error_str = f"An unexpected error occurred during ElevenLabs TTS generation: {e}"
        print(error_str)
        return None, error_str
