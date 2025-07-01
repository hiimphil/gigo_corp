# elevenlabs_module.py
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import tempfile
import streamlit as st

# --- Voice Configuration ---
CHARACTER_VOICE_MAP = {
    'a': '0rOfEdoZRnNF0sbnFR5B', # Artie
    'b': 'PdXvwvHc8PDiZVI7iUTD', # B00L
    'c': 'Px4v5nXnQ6QfAZufyV2u', # Cling
    'd': '7hAUbSMdewpdCy8Y0nDx', # Dusty
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
    Generates an audio file from text using ElevenLabs TTS (Text-to-Speech).
    """
    if not text or not text.strip():
        return None, None 

    client, error = get_elevenlabs_client()
    if error:
        return None, error

    voice_id_str = CHARACTER_VOICE_MAP.get(character_id.lower(), CHARACTER_VOICE_MAP['default'])

    if "placeholder" in voice_id_str:
        return None, f"Character '{character_id}' is using a placeholder Voice ID. Please update it."

    try:
        audio_bytes = client.text_to_speech.convert(
            voice_id=voice_id_str,
            text=text,
            model_id="eleven_multilingual_v2"
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
            save(audio_bytes, temp_audio_file.name)
            return temp_audio_file.name, None
    except Exception as e:
        return None, f"An unexpected error occurred during ElevenLabs TTS generation: {e}"


def change_voice_from_audio(character_id, audio_path):
    """
    Transforms the voice in an audio file to a different character's voice
    using ElevenLabs Speech to Speech.
    """
    if not audio_path or not os.path.exists(audio_path):
        return None, "Source audio file not found."

    client, error = get_elevenlabs_client()
    if error:
        return None, error

    voice_id_str = CHARACTER_VOICE_MAP.get(character_id.lower(), CHARACTER_VOICE_MAP['default'])
    if "placeholder" in voice_id_str:
        return None, f"Character '{character_id}' is using a placeholder Voice ID. Please update it."

    try:
        with open(audio_path, 'rb') as audio_file:
            # Convert the source audio file to the target voice
            audio_bytes = client.speech_to_speech.convert(
                voice_id=voice_id_str,
                audio=audio_file, # Pass the file object directly
                model_id="eleven_multilingual_sts_v2" 
            )

        # Save the transformed audio to a new temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
            save(audio_bytes, temp_audio_file.name)
            return temp_audio_file.name, None
    except Exception as e:
        return None, f"An unexpected error occurred during ElevenLabs STS generation: {e}"

