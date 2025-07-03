# elevenlabs_module.py
import os
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import tempfile
import streamlit as st
import hashlib
import database_module as db # Import our database module
import requests # To download cached files

# --- Voice Configuration ---
# TODO: Replace these placeholder IDs with your actual ElevenLabs Voice IDs.
# You can find Voice IDs in your VoiceLab on the ElevenLabs website.
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

def generate_speech_for_line(character_id, text, force_regenerate=False):
    """
    Generates an audio file from text using ElevenLabs TTS, with caching.
    Returns the file path, an error message, and a status ('cached' or 'generated').
    """
    if not text or not text.strip():
        return None, None, None

    # Create a unique ID for this text and voice combination
    unique_string = f"{text}-{character_id}"
    text_hash = hashlib.md5(unique_string.encode()).hexdigest()

    # --- Caching Logic ---
    if not force_regenerate:
        cached_url = db.get_audio_cache_entry(text_hash)
        if cached_url:
            print(f"CACHE HIT: Found audio for '{text}'")
            try:
                # Download the cached file to a temporary location
                response = requests.get(cached_url)
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
                    temp_audio_file.write(response.content)
                    # Return 'cached' status
                    return temp_audio_file.name, None, "cached"
            except Exception as e:
                print(f"Failed to download cached audio, will regenerate. Error: {e}")
    
    # --- Generation Logic (if cache miss or force regenerate) ---
    print(f"CACHE MISS: Generating new audio for '{text}'")
    client, error = get_elevenlabs_client()
    if error:
        return None, error, None

    voice_id_str = CHARACTER_VOICE_MAP.get(character_id.lower(), CHARACTER_VOICE_MAP['default'])

    if "placeholder" in voice_id_str:
        return None, f"Character '{character_id}' is using a placeholder Voice ID.", None

    try:
        audio_bytes = client.text_to_speech.convert(
            voice_id=voice_id_str,
            text=text,
            model_id="eleven_multilingual_v2" #trying to get access to v3 API
        )
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
            save(audio_bytes, temp_audio_file.name)
            local_path = temp_audio_file.name

        # Upload the new file to Firebase Storage
        download_url, upload_error = db.upload_audio_to_storage(local_path, text_hash)
        if upload_error:
            return None, upload_error, None
        
        # Save the new URL to the Firestore cache
        db.set_audio_cache_entry(text_hash, download_url, text)

        # Return 'generated' status
        return local_path, None, "generated"
    except Exception as e:
        return None, f"An unexpected error occurred during ElevenLabs TTS generation: {e}", None

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
            audio_bytes = client.speech_to_speech.convert(
                voice_id=voice_id_str,
                audio=audio_file,
                model_id="eleven_multilingual_sts_v2" 
            )

        # Save the transformed audio to a new temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
            save(audio_bytes, temp_audio_file.name)
            return temp_audio_file.name, None

