# video_module.py
import os
import random

# --- START OF MOVIEPY FIX ---
# We explicitly tell moviepy where to find the ImageMagick binary.
# This is a robust way to fix path issues in containerized environments like Streamlit Cloud.
from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": r"/usr/bin/convert"})
# --- END OF MOVIEPY FIX ---

from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips
import comic_generator_module as cgm

# --- Configuration ---
FPS = 12  # Frames per second for the animation. 12 is good for a simple cartoon style.

def find_animation_frames(character, talking_state, direction, action):
    """
    Finds a sequence of images for animation.
    If multiple images are in the folder, it's an animation.
    If only one, it's a static shot.
    Returns a list of image paths.
    """
    base_path, _ = cgm.find_image_path(character.lower(), talking_state.lower(), direction.lower(), action.lower())

    if not base_path:
        return []

    image_dir = os.path.dirname(base_path)

    if os.path.isdir(image_dir):
        images = sorted([
            os.path.join(image_dir, f) for f in os.listdir(image_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        return images
    
    return []


def create_scene_clip(character, action, dialogue, audio_path):
    """
    Creates a single video clip for one line of dialogue.
    """
    talking_state = "talking" if dialogue else "nottalking"
    direction = cgm.determine_logical_direction(character.lower(), None)
    frame_paths = find_animation_frames(character, talking_state, direction, action)
    
    if not frame_paths:
        return None, f"Could not find any images for {character} in state {talking_state}/{action}"

    if audio_path and os.path.exists(audio_path):
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
    else:
        duration = 1.5
        audio_clip = None

    num_frames_in_sequence = len(frame_paths)
    total_frames_in_clip = int(duration * FPS)
    
    final_frame_list = []
    if num_frames_in_sequence == 1:
        final_frame_list = [frame_paths[0]] * total_frames_in_clip
    else:
        for i in range(total_frames_in_clip):
            frame_index = i % num_frames_in_sequence
            final_frame_list.append(frame_paths[frame_index])

    if not final_frame_list:
        return None, "Failed to generate frame list for the scene."

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

    for i, line in enumerate(lines):
        char, action, _, dialogue = cgm.parse_script_line(line)
        if not char:
            continue

        audio_path = audio_paths_dict.get(i)
        
        scene_clip, error = create_scene_clip(char, action, dialogue, audio_path)
        if error:
            return None, error
        
        if scene_clip:
            scene_clips.append(scene_clip)

    if not scene_clips:
        return None, "No scenes were generated. Check your image paths and script."

    final_video = concatenate_videoclips(scene_clips)
    
    output_dir = "Output_Cartoons"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = random.randint(1000, 9999)
    final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")

    try:
        final_video.write_videofile(
            final_video_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=FPS
        )
        return final_video_path, None
    except Exception as e:
        return None, f"MoviePy failed to write the video file: {e}"
