# video_module.py
import os
import random
import numpy as np
from PIL import Image
from moviepy.editor import (ImageSequenceClip, AudioFileClip, VideoFileClip, 
                            CompositeVideoClip, concatenate_videoclips, CompositeAudioClip,
                            concatenate_audioclips)
from moviepy.audio.fx.all import volumex
import comic_generator_module as cgm
import math
import tempfile 
import shutil 
import subprocess

# --- Configuration ---
FPS = 12
STANDARD_WIDTH = cgm.PANEL_WIDTH
STANDARD_HEIGHT = cgm.PANEL_HEIGHT
BACKGROUND_AUDIO_VOLUME = 0.1

# --- Default Asset Paths ---
DEFAULT_BG_AUDIO_PATH = "SFX/buzz.mp3"
OPENING_SEQUENCE_PATH = "Video/OpeningSequence.mp4"
CARTOON_IMAGE_BASE_PATH = "Cartoon_Images/"

# --- Tracking Dot Configuration ---
LEFT_DOT_COLOR = np.array([0, 255, 0])  # Pure Green
RIGHT_DOT_COLOR = np.array([0, 0, 255]) # Pure Blue
REFERENCE_DOT_DISTANCE = 20.0 

# --- Lip-Sync Thresholds ---
SILENCE_THRESHOLD = 0.01
SMALL_MOUTH_THRESHOLD = 0.1

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
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, direction, action, "base.png")
    if os.path.exists(path):
        return path, None
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

def create_scene_clip_memory_efficient(character, action, direction_override, dialogue, audio_path, prev_char):
    """
    Generates a silent video clip for a single scene. Audio is handled separately.
    """
    direction = direction_override or cgm.determine_logical_direction(character.lower(), prev_char)
    
    base_image_path, error = find_base_image_path(character, direction, action)
    if error: return None, error, None
    
    try:
        base_image_pil = Image.open(base_image_path).convert("RGB")

        # --- FFMPEG FIX: Ensure video dimensions are even numbers ---
        w, h = base_image_pil.size
        if w % 2 != 0: w -= 1
        if h % 2 != 0: h -= 1
        base_image_pil = base_image_pil.crop((0, 0, w, h))
        # --- END OF FIX ---

        base_image_np = np.array(base_image_pil)
        left_dot, right_dot = find_tracking_dots(base_image_np)
        if not left_dot or not right_dot:
            return None, f"Tracking dots not found in {base_image_path}", None
    except Exception as e:
        return None, f"Error processing base image {base_image_path}: {e}", None

    dx = right_dot[0] - left_dot[0]
    dy = right_dot[1] - left_dot[1]
    actual_dot_distance = math.sqrt(dx**2 + dy**2)
    
    scale_factor = actual_dot_distance / REFERENCE_DOT_DISTANCE
    rotation_angle = math.degrees(math.atan2(dy, dx))
    position_center = ((left_dot[0] + right_dot[0]) / 2, (left_dot[1] + right_dot[1]) / 2)

    # --- REFACTORED AUDIO HANDLING ---
    dialogue_clip = None
    if audio_path and os.path.exists(audio_path):
        try:
            dialogue_clip = AudioFileClip(audio_path)
            duration = dialogue_clip.duration
        except Exception as e:
            return None, f"Error loading audio clip {audio_path}: {e}", None
    else:
        duration = 1.5 # Default pause duration

    total_frames_in_scene = int(duration * FPS)
    
    mouth_shapes = {}
    for shape_name in ["closed", "open-small", "open-large"]:
        path, error = find_mouth_shape_path(character, shape_name)
        if error: return None, error, None
        mouth_shapes[shape_name] = Image.open(path).convert("RGBA")

    # Get audio volume data once to avoid re-opening the file
    audio_volumes = []
    if dialogue_clip:
        for i in range(total_frames_in_scene):
            current_time = float(i) / FPS
            sample = dialogue_clip.get_frame(current_time)
            audio_volumes.append(np.max(np.abs(sample)))

    final_frames = []
    for i in range(total_frames_in_scene):
        if dialogue_clip:
            volume = audio_volumes[i]
            if volume < SILENCE_THRESHOLD: mouth_shape_name = "closed"
            elif volume < SMALL_MOUTH_THRESHOLD: mouth_shape_name = "open-small"
            else: mouth_shape_name = "open-large"
        else:
            mouth_shape_name = "closed"
            
        frame_pil = Image.fromarray(base_image_np)
        mouth_pil = mouth_shapes[mouth_shape_name]
        
        mouth_pil = mouth_pil.resize((int(mouth_pil.width * scale_factor), int(mouth_pil.height * scale_factor)), Image.Resampling.LANCZOS)
        mouth_pil = mouth_pil.rotate(rotation_angle, expand=True, resample=Image.BICUBIC)
        
        mouth_w, mouth_h = mouth_pil.size
        paste_pos = (int(position_center[0] - mouth_w / 2), int(position_center[1] - mouth_h / 2))
        
        frame_pil.paste(mouth_pil, paste_pos, mouth_pil)
        final_frames.append(np.array(frame_pil))

    if not final_frames:
        return None, "Failed to generate any frames for the scene.", None

    # Return a silent video clip and the separate audio clip
    silent_video_clip = ImageSequenceClip(final_frames, fps=FPS)
    return silent_video_clip, None, dialogue_clip


def create_video_from_script(script_text, audio_paths_dict, background_audio_path=None):
    """
    Generates a full cartoon video using the highly memory-efficient, frame-by-frame approach.
    """
    temp_dir = tempfile.mkdtemp()
    video_scenes = []
    audio_scenes = []
    previous_character = None

    try:
        lines = script_text.strip().split('\n')
        for i, line in enumerate(lines):
            char, action, direction_override, dialogue = cgm.parse_script_line(line)
            if not char: continue
            
            audio_path = audio_paths_dict.get(i)
            # Get the silent video and the audio clip separately
            video_clip, error, audio_clip = create_scene_clip_memory_efficient(char, action, direction_override, dialogue, audio_path, previous_character)
            
            if error: return None, error
            if video_clip: video_scenes.append(video_clip)
            if audio_clip: audio_scenes.append(audio_clip)
            
            previous_character = char.lower()

        if not video_scenes:
            return None, "No video scenes were generated."

        # --- REFACTORED WORKFLOW ---
        # 1. Stitch all the silent video scenes together
        main_video_body = concatenate_videoclips(video_scenes)
        
        # 2. Stitch all the dialogue audio clips together
        if audio_scenes:
            dialogue_track = concatenate_audioclips(audio_scenes)
            main_video_body = main_video_body.set_audio(dialogue_track)

        # 3. Mix in the background audio
        final_bg_audio_path = background_audio_path or (DEFAULT_BG_AUDIO_PATH if os.path.exists(DEFAULT_BG_AUDIO_PATH) else None)
        if final_bg_audio_path:
            try:
                background_clip = AudioFileClip(final_bg_audio_path).fx(volumex, BACKGROUND_AUDIO_VOLUME)
                background_clip = background_clip.set_duration(main_video_body.duration)
                
                if main_video_body.audio:
                    combined_audio = CompositeAudioClip([main_video_body.audio, background_clip])
                    main_video_body.audio = combined_audio
                else:
                    main_video_body.audio = background_clip
            except Exception as e:
                return None, f"Failed to process background audio: {e}"

        # 4. Prepend the opening sequence
        final_clips_to_join = []
        if os.path.exists(OPENING_SEQUENCE_PATH):
            try:
                opening_clip = VideoFileClip(OPENING_SEQUENCE_PATH)
                if opening_clip.size != [STANDARD_WIDTH, STANDARD_HEIGHT]:
                     return None, f"OpeningSequence.mp4 is not {STANDARD_WIDTH}x{STANDARD_HEIGHT}."
                final_clips_to_join.append(opening_clip)
            except Exception as e:
                return None, f"Failed to load opening sequence: {e}"

        final_clips_to_join.append(main_video_body)
        final_video = concatenate_videoclips(final_clips_to_join)

        # 5. Write the final file
        output_dir = "Output_Cartoons"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = random.randint(1000, 9999)
        final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")

        final_video.write_videofile(
            final_video_path, codec='libx264', audio_codec='aac',
            temp_audiofile='temp-audio.m4a', remove_temp=True, fps=FPS, logger=None
        )
        return final_video_path, None

    except Exception as e:
        return None, f"An unexpected error occurred during video creation: {e}"
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
