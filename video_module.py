# video_module.py
import os
import random
import numpy as np
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips
import comic_generator_module as cgm

# --- Configuration ---
FPS = 12
STANDARD_WIDTH = cgm.PANEL_WIDTH
STANDARD_HEIGHT = cgm.PANEL_HEIGHT

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
    Creates a single video clip for one line of dialogue, now with robust frame resizing
    and correct direction override logic.
    """
    talking_state = "talking" if dialogue else "nottalking"
    
    # --- DIRECTION LOGIC FIX ---
    # The direction is now correctly determined by using the override first,
    # then falling back to the conversational logic.
    direction = direction_override or cgm.determine_logical_direction(character.lower(), prev_char)
    
    frame_paths = find_animation_frames(character, talking_state, direction, action)
    if not frame_paths:
        return None, f"Could not find any images for {character} in state {talking_state}/{action}"

    if audio_path and os.path.exists(audio_path):
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
    else:
        duration = 1.5
        audio_clip = None

    # --- MODERN RESIZING FIX ---
    # We now manually resize each frame using the latest Pillow library before passing it to MoviePy.
    # This avoids MoviePy's internal, outdated call to Image.ANTIALIAS.
    unique_numpy_frames = []
    for path in frame_paths:
        try:
            with Image.open(path) as img:
                # Use Image.Resampling.LANCZOS, the modern equivalent of ANTIALIAS
                resized_img = img.resize((STANDARD_WIDTH, STANDARD_HEIGHT), Image.Resampling.LANCZOS)
                # Convert the Pillow image to a NumPy array, which MoviePy can use
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
    if audio_clip:
        video_clip = video_clip.set_audio(audio_clip)

    return video_clip, None

def create_video_from_script(script_text, audio_paths_dict):
    """
    Generates a full cartoon video from a script and its corresponding audio files.
    """
    lines = script_text.strip().split('\n')
    scene_clips = []
    previous_character = None

    for i, line in enumerate(lines):
        # Now correctly capturing the direction_override from the parsed line
        char, action, direction_override, dialogue = cgm.parse_script_line(line)
        if not char:
            continue
        audio_path = audio_paths_dict.get(i)
        
        # Pass the direction_override to the scene creation function
        scene_clip, error = create_scene_clip(char, action, direction_override, dialogue, audio_path, previous_character)
        
        if error:
            return None, error
        if scene_clip:
            scene_clips.append(scene_clip)
        previous_character = char.lower()

    if not scene_clips:
        return None, "No scenes were generated. Check your image paths and script."

    final_video = concatenate_videoclips(scene_clips)
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
