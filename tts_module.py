# tts_module.py
import os
import openai
import tempfile
from ai_script_module import load_api_key_and_init_client

# --- Voice Configuration ---
# Here we can assign a specific voice to each character.
# These are the standard voices available from OpenAI's TTS API.
# Feel free to change these to find the voices that best fit your characters.
CHARACTER_VOICE_MAP = {
    'a': 'echo',    # A friendly and engaging male voice.
    'b': 'onyx',    # A deep and resonant male voice.
    'c': 'fable',   # A warm, storyteller-like male voice.
    'd': 'shimmer', # A deep, emotive female voice.
    'default': 'alloy' # A neutral, balanced male voice as a fallback.
}

def generate_speech_for_line(character_id, text):
    """
    Generates an audio file from text using OpenAI's TTS and a specific character voice.
    
    Args:
        character_id (str): The character's ID (e.g., 'a', 'b').
        text (str): The line of dialogue to be converted to speech.

    Returns:
        A tuple containing (file_path, error_message).
        If successful, file_path is the path to the temporary audio file and error_message is None.
        If it fails, file_path is None and error_message contains the error details.
    """
    if not text or not text.strip():
        # No dialogue to speak, so we can return successfully with no audio path.
        # This will represent a pause in the final animation.
        return None, None

    client, error_msg = load_api_key_and_init_client()
    if error_msg:
        return None, f"TTS Failed: {error_msg}"

    # Select the voice based on the character ID, with a fallback to the default.
    voice_id = CHARACTER_VOICE_MAP.get(character_id.lower(), CHARACTER_VOICE_MAP['default'])

    try:
        # Create the TTS API request
        response = client.audio.speech.create(
            model="tts-1",  # "tts-1" is fast and high quality. "tts-1-hd" is higher quality but slower.
            voice=voice_id,
            input=text
        )

        # Create a temporary file to save the audio
        # Using a temporary file is good practice for managing intermediate files.
        # We give it a .mp3 extension so it can be handled correctly.
        temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_audio_path = temp_audio_file.name
        temp_audio_file.close() # Close the file so the API can write to it.

        # Stream the audio content directly to our temporary file
        response.stream_to_file(temp_audio_path)

        print(f"Generated audio for '{text}' at: {temp_audio_path}")
        return temp_audio_path, None

    except Exception as e:
        error_str = f"An unexpected error occurred during TTS generation: {e}"
        print(error_str)
        return None, error_str
