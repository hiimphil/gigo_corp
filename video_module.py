# video_module.py
import os
import random
import numpy as np
from PIL import Image
from moviepy.editor import (ImageSequenceClip, AudioFileClip, VideoFileClip, 
                            CompositeVideoClip, concatenate_videoclips)
from moviepy.audio.fx.all import volumex
import comic_generator_module as cgm
import math

# --- Configuration ---
FPS = 12
STANDARD_WIDTH = cgm.PANEL_WIDTH
STANDARD_HEIGHT = cgm.PANEL_HEIGHT
BACKGROUND_AUDIO_VOLUME = 0.5 # Set background audio to 50%

# --- Default Asset Paths ---
DEFAULT_BG_AUDIO_PATH = "SFX/buzz.mp3"
OPENING_SEQUENCE_PATH = "Video/OpeningSequence.mp4"
CARTOON_IMAGE_BASE_PATH = "Cartoon_Images/"

# --- Tracking Dot Configuration ---
LEFT_DOT_COLOR = np.array([0, 255, 0])  # Pure Green
RIGHT_DOT_COLOR = np.array([0, 0, 255]) # Pure Blue
REFERENCE_DOT_DISTANCE = 20.0 

# --- Lip-Sync Thresholds ---
# These values determine which mouth shape is used based on audio volume.
# You can tweak these to get the best visual result.
SILENCE_THRESHOLD = 0.01  # Volume below this is considered silent (closed mouth)
SMALL_MOUTH_THRESHOLD = 0.1 # Volume above SILENCE but below this uses open-small

def find_tracking_dots(image_array):
    """Scans a numpy image array to find the coordinates of the tracking dots."""
    left_dot_coords = np.where(np.all(image_array == LEFT_DOT_COLOR, axis=-1))
    right_dot_coords = np.where(np.all(image_array == RIGHT_DOT_COLOR, axis=-1))

    if left_dot_coords[0].size == 0 or right_dot_coords[0].size == 0:
        return None, None

    left_pos = (left_dot_coords[1][0], left_dot_coords[0][0])
    right_pos = (right_dot_coords[1][0], right_dot_coords[0][0])
    return left_pos, right_pos

def find_base_image_path(character, direction, action):
    """Finds the path to the mouthless base image for a character."""
    # This can be expanded with fallbacks similar to the comic generator if needed
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, direction, action, "base.png")
    if os.path.exists(path):
        return path, None
    # Fallback to normal action
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, direction, "normal", "base.png")
    if os.path.exists(path):
        return path, None
    return None, f"No base image found for {character}/{direction}/{action} or normal fallback."

def find_mouth_shape_path(character, mouth_shape):
    """Finds the path to a specific mouth shape for a character."""
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, "mouths", f"{mouth_shape}.png")
    if os.path.exists(path):
        return path, None
    return None, f"Mouth shape '{mouth_shape}' not found for character '{character}'"

def create_scene_clip(character, action, direction_override, dialogue, audio_path, prev_char):
    """Creates a single video clip for one line of dialogue using dot tracking and lip-sync."""
    direction = direction_override or cgm.determine_logical_direction(character.lower(), prev_char)
    
    # --- Load Base Image and Find Dots ---
    base_image_path, error = find_base_image_path(character, direction, action)
    if error: return None, error
    
    try:
        base_image_pil = Image.open(base_image_path).convert("RGB")
        base_image_np = np.array(base_image_pil)
        left_dot, right_dot = find_tracking_dots(base_image_np)
        if not left_dot or not right_dot:
            return None, f"Tracking dots not found in {base_image_path}"
    except Exception as e:
        return None, f"Error processing base image {base_image_path}: {e}"

    # --- Calculate Transformation ---
    dx = right_dot[0] - left_dot[0]
    dy = right_dot[1] - left_dot[1]
    actual_dot_distance = math.sqrt(dx**2 + dy**2)
    
    scale_factor = actual_dot_distance / REFERENCE_DOT_DISTANCE
    rotation_angle = math.degrees(math.atan2(dy, dx))
    position_center = ((left_dot[0] + right_dot[0]) / 2, (left_dot[1] + right_dot[1]) / 2)

    # --- Determine Scene Duration ---
    if audio_path and os.path.exists(audio_path):
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
    else:
        duration = 1.5
        audio_clip = None

    # --- Lip-Sync Frame Generation ---
    final_frames = []
    total_frames_in_scene = int(duration * FPS)
    
    # Load mouth shapes once
    mouth_shapes = {}
    for shape_name in ["closed", "open-small", "open-large"]:
        path, error = find_mouth_shape_path(character, shape_name)
        if error: return None, error
        mouth_shapes[shape_name] = np.array(Image.open(path).convert("RGBA"))

    for i in range(total_frames_in_scene):
        current_time = float(i) / FPS
        
        # Determine which mouth to use based on audio volume
        if audio_clip:
            # Get a small sample of the audio at the current time
            sample = audio_clip.get_frame(current_time)
            # Get the max volume from the sample (normalized to 0-1)
            volume = np.max(np.abs(sample))
            
            if volume < SILENCE_THRESHOLD:
                mouth_shape_name = "closed"
            elif volume < SMALL_MOUTH_THRESHOLD:
                mouth_shape_name = "open-small"
            else:
                mouth_shape_name = "open-large"
        else:
            # If no audio, the mouth is always closed
            mouth_shape_name = "closed"
            
        # Create the frame by compositing the mouth onto the base
        frame_pil = Image.fromarray(base_image_np)
        mouth_pil = Image.fromarray(mouth_shapes[mouth_shape_name])
        
        # Apply transformations to the mouth
        mouth_pil = mouth_pil.resize((int(mouth_pil.width * scale_factor), int(mouth_pil.height * scale_factor)), Image.Resampling.LANCZOS)
        mouth_pil = mouth_pil.rotate(rotation_angle, expand=True, resample=Image.BICUBIC)
        
        # Calculate top-left position for pasting
        mouth_w, mouth_h = mouth_pil.size
        paste_pos = (int(position_center[0] - mouth_w / 2), int(position_center[1] - mouth_h / 2))
        
        # Paste the mouth onto the base image
        frame_pil.paste(mouth_pil, paste_pos, mouth_pil)
        final_frames.append(np.array(frame_pil))

    if not final_frames:
        return None, "Failed to generate any frames for the scene."

    scene_video = ImageSequenceClip(final_frames, fps=FPS)
    if audio_clip:
        scene_video = scene_video.set_audio(audio_clip)

    return scene_video, None


def create_video_from_script(script_text, audio_paths_dict, background_audio_path=None):
    """Generates a full cartoon video using the new dot tracking logic."""
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
