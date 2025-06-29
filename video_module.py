# video_module.py
import os
import random
import numpy as np
from PIL import Image
from moviepy.editor import (ImageSequenceClip, AudioFileClip, VideoFileClip, 
                            CompositeAudioClip, concatenate_videoclips)
from moviepy.audio.fx.all import volumex
import comic_generator_module as cgm

# --- Configuration ---
FPS = 12
STANDARD_WIDTH = cgm.PANEL_WIDTH
STANDARD_HEIGHT = cgm.PANEL_HEIGHT
BACKGROUND_AUDIO_VOLUME = 0.1 # Set background audio to 10%

# --- Default Asset Paths ---
DEFAULT_BG_AUDIO_PATH = "SFX/buzz.mp3"
OPENING_SEQUENCE_PATH = "Video/OpeningSequence.mp4"

def find_animation_frames(character, talking_state, direction, action):
    """Finds a sequence of images for animation."""
    base_path, _ = cgm.find_image_path(character.lower(), talking_state.lower(), direction.lower(), action.lower())
    if not base_path:
        return []
    image_dir = os.path.dirname(base_path)
    if os.path.isdir(image_dir):
        return sorted([
            os.path.join(image_dir, f) for f in os.listdir(image_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
    return []

def create_scene_clip(character, action, direction_override, dialogue, audio_path, prev_char):
    """
    Creates a single video clip for one line of dialogue.
    """
    talking_state = "talking" if dialogue else "nottalking"
    direction = direction_override or cgm.determine_logical_direction(character.lower(), prev_char)
    frame_paths = find_animation_frames(character, talking_state, direction, action)
    if not frame_paths:
        return None, f"Could not find any images for {character} in state {talking_state}/{action}"

    if audio_path and os.path.exists(audio_path):
        dialogue_clip = AudioFileClip(audio_path)
        duration = dialogue_clip.duration
    else:
        duration = 1.5
        dialogue_clip = None

    unique_numpy_frames = []
    for path in frame_paths:
        try:
            with Image.open(path) as img:
                resized_img = img.resize((STANDARD_WIDTH, STANDARD_HEIGHT), Image.Resampling.LANCZOS)
                unique_numpy_frames.append(np.array(resized_img))
        except Exception as e:
            return None, f"Failed to open or resize image {path}: {e}"

    num_unique_frames = len(unique_numpy_frames)
    total_frames_in_scene = int(duration * FPS)
    final_frame_list = []
    if num_unique_frames == 1:
        final_frame_list = [unique_numpy_frames[0]] * total_frames_in_scene
    else:
        for i in range(total_frames_in_scene):
            frame_index = i % num_unique_frames
            final_frame_list.append(unique_numpy_frames[frame_index])

    if not final_frame_list:
        return None, "Failed to generate numpy frame list for the scene."

    video_clip = ImageSequenceClip(final_frame_list, fps=FPS)
    if dialogue_clip:
        video_clip = video_clip.set_audio(dialogue_clip)

    return video_clip, None

def create_video_from_script(script_text, audio_paths_dict, background_audio_path=None):
    """
    Generates a full cartoon video, now with an optional background audio track and opening sequence.
    """
    lines = script_text.strip().split('\n')
    scene_clips = []
    previous_character = None

    for i, line in enumerate(lines):
        char, action, direction_override, dialogue = cgm.parse_script_line(line)
        if not char:
            continue
        audio_path = audio_paths_dict.get(i)
        scene_clip, error = create_scene_clip(char, action, direction_override, dialogue, audio_path, previous_character)
        if error:
            return None, error
        if scene_clip:
            scene_clips.append(scene_clip)
        previous_character = char.lower()

    if not scene_clips:
        return None, "No scenes were generated. Check your image paths and script."

    # Create the main cartoon body by combining the scenes
    main_cartoon_body = concatenate_videoclips(scene_clips)

    # Determine which background audio to use (uploaded or default)
    final_bg_audio_path = background_audio_path or (DEFAULT_BG_AUDIO_PATH if os.path.exists(DEFAULT_BG_AUDIO_PATH) else None)
    
    if final_bg_audio_path:
        try:
            background_clip = AudioFileClip(final_bg_audio_path).fx(volumex, BACKGROUND_AUDIO_VOLUME)
            background_clip = background_clip.set_duration(main_cartoon_body.duration)

            if main_cartoon_body.audio:
                # Mix the dialogue with the background music
                combined_audio = CompositeAudioClip([main_cartoon_body.audio, background_clip])
                main_cartoon_body.audio = combined_audio
            else:
                # If no dialogue, just use the background music
                main_cartoon_body.audio = background_clip
            
        except Exception as e:
            return None, f"Failed to process background audio: {e}"

    # --- Add Opening Sequence ---
    final_clips_to_join = []
    if os.path.exists(OPENING_SEQUENCE_PATH):
        try:
            # Load the opening sequence and ensure it's the correct size
            opening_clip = VideoFileClip(OPENING_SEQUENCE_PATH).resize(width=STANDARD_WIDTH, height=STANDARD_HEIGHT)
            final_clips_to_join.append(opening_clip)
        except Exception as e:
            return None, f"Failed to load opening sequence video: {e}"

    final_clips_to_join.append(main_cartoon_body)
    
    # Concatenate the final list of clips (opening sequence + main cartoon)
    final_video = concatenate_videoclips(final_clips_to_join)

    output_dir = "Output_Cartoons"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = random.randint(1000, 9999)
    final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")

    try:
        final_video.write_videofile(
            final_video_path, codec='libx264', audio_codec='aac',
            temp_audiofile='temp-audio.m4a', remove_temp=True, fps=FPS
        )
        return final_video_path, None
    except Exception as e:
        return None, f"MoviePy failed to write the video file: {e}"
