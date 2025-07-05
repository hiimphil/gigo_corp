# video_module.py
import os
import random
import numpy as np
from PIL import Image
from moviepy.editor import (ImageSequenceClip, AudioFileClip, VideoFileClip, 
                            CompositeVideoClip, concatenate_videoclips, CompositeAudioClip,
                            concatenate_audioclips)
from moviepy.audio.AudioClip import AudioArrayClip
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
BACKGROUND_AUDIO_VOLUME = 0.5

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

# --- Helper Functions (find_tracking_dots, find_base_image_path, etc.) ---
# ... (These functions are unchanged and remain here) ...
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
    return None, f"No base image found for {character}/{direction}/{action} or normal."

def find_mouth_shape_path(character, mouth_shape):
    """Finds the path to a specific mouth shape for a character."""
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, "mouths", f"{mouth_shape}.png")
    if os.path.exists(path):
        return path, None
    return None, f"Mouth shape '{mouth_shape}' not found for character '{character}'"

def get_mouth_shapes_for_scene(audio_path, duration):
    """Analyzes an audio file and returns a frame-by-frame list of mouth shapes."""
    if not audio_path or not os.path.exists(audio_path):
        return ["closed"] * int(duration * FPS), None

    try:
        with AudioFileClip(audio_path) as audio_clip:
            total_frames = int(duration * FPS)
            mouth_shapes = []
            for i in range(total_frames):
                current_time = float(i) / FPS
                sample = audio_clip.get_frame(current_time)
                if sample.ndim > 1:
                    sample = sample.mean(axis=1)
                volume = np.max(np.abs(sample))
                
                if volume < SILENCE_THRESHOLD:
                    mouth_shapes.append("closed")
                elif volume < SMALL_MOUTH_THRESHOLD:
                    mouth_shapes.append("open-small")
                else:
                    mouth_shapes.append("open-large")
            
            return mouth_shapes, None
    except Exception as e:
        return None, f"Error analyzing audio clip {audio_path}: {e}"

# --- Single Scene Rendering Function ---
def render_single_scene(line, audio_path, duration, scene_index):
    """Generates a single, self-contained video clip for one line of the script."""
    temp_dir = tempfile.mkdtemp()
    try:
        char, action, direction_override, _ = cgm.parse_script_line(line)
        if not char: return None, "Could not parse line."

        mouth_shapes, error = get_mouth_shapes_for_scene(audio_path, duration)
        if error: return None, error
        
        # For now, we assume the previous character is None to keep scenes independent
        direction = direction_override or cgm.determine_logical_direction(char.lower(), None)
        base_image_path, error = find_base_image_path(char, direction, action)
        if error: return None, error

        base_image_pil = Image.open(base_image_path).convert("RGB")
        w, h = base_image_pil.size
        if w % 2 != 0: w -= 1
        if h % 2 != 0: h -= 1
        base_image_pil = base_image_pil.crop((0, 0, w, h))
        base_image_np = np.array(base_image_pil)
        
        left_dot, right_dot = find_tracking_dots(base_image_np)
        if not left_dot or not right_dot: return None, f"Tracking dots not found in {base_image_path}"

        dx, dy = right_dot[0] - left_dot[0], right_dot[1] - left_dot[1]
        scale = math.sqrt(dx**2 + dy**2) / REFERENCE_DOT_DISTANCE
        angle = -math.degrees(math.atan2(dy, dx))
        center = ((left_dot[0] + right_dot[0]) / 2, (left_dot[1] + right_dot[1]) / 2)
        
        mouth_pils = {name: Image.open(find_mouth_shape_path(char, name)[0]).convert("RGBA") for name in set(mouth_shapes)}

        final_frames = []
        for mouth_shape_name in mouth_shapes:
            frame_pil = Image.fromarray(base_image_np)
            mouth_pil = mouth_pils[mouth_shape_name]
            transformed_mouth = mouth_pil.resize((int(mouth_pil.width * scale), int(mouth_pil.height * scale)), Image.Resampling.LANCZOS)
            transformed_mouth = transformed_mouth.rotate(angle, expand=True, resample=Image.BICUBIC)
            mouth_w, mouth_h = transformed_mouth.size
            paste_pos = (int(center[0] - mouth_w / 2), int(center[1] - mouth_h / 2))
            frame_pil.paste(transformed_mouth, paste_pos, transformed_mouth)
            final_frames.append(np.array(frame_pil))

        if not final_frames:
            return None, "Failed to generate any frames for the scene."

        # Create the silent video clip from the frames
        video_clip = ImageSequenceClip(final_frames, fps=FPS)

        # --- NEW LOGIC: Attach either the real audio or silent audio ---
        if audio_path:
            dialogue_clip = AudioFileClip(audio_path)
            video_clip = video_clip.set_audio(dialogue_clip)
        else:
            # Create a silent audio clip of the correct duration
            silent_audio = AudioArrayClip(np.zeros((int(duration * 44100), 1)), fps=44100)
            video_clip = video_clip.set_audio(silent_audio.set_duration(duration))

        # Save the complete scene (with audio) to a file
        output_dir = "Output_Scenes"
        os.makedirs(output_dir, exist_ok=True)
        scene_video_path = os.path.join(output_dir, f"scene_{scene_index}.mp4")
        video_clip.write_videofile(scene_video_path, codec='libx264', audio_codec='aac', fps=FPS, logger=None)

        return scene_video_path, None

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# --- NEW: Final Assembly Function ---
def assemble_final_cartoon(scene_paths, background_audio_path=None):
    """
    Assembles pre-rendered scene clips into a final cartoon.
    """
    try:
        # Debug info
        print(f"DEBUG: Assembling {len(scene_paths)} scenes:")
        for i, path in enumerate(scene_paths):
            print(f"  Scene {i}: {path} (exists: {os.path.exists(path)})")
        # --- SIMPLIFIED ASSEMBLY PROCESS ---
        # 1. Load all scene clips (which now all have audio tracks)
        scene_clips = []
        for i, path in enumerate(scene_paths):
            if not os.path.exists(path):
                return None, f"Scene {i} file not found: {path}"
            try:
                clip = VideoFileClip(path)
                if clip is None:
                    return None, f"Scene {i} failed to load: {path}"
                scene_clips.append(clip)
            except Exception as e:
                return None, f"Error loading scene {i} ({path}): {e}"
        
        # 2. Prepend the opening sequence
        if os.path.exists(OPENING_SEQUENCE_PATH):
            try:
                opening_clip = VideoFileClip(OPENING_SEQUENCE_PATH)
                if opening_clip.size != [STANDARD_WIDTH, STANDARD_HEIGHT]:
                     return None, f"OpeningSequence.mp4 is not {STANDARD_WIDTH}x{STANDARD_HEIGHT}."
                scene_clips.insert(0, opening_clip)
            except Exception as e:
                return None, f"Failed to load opening sequence: {e}"

        # 3. Validate and concatenate all video clips
        if not scene_clips:
            return None, "No valid scene clips found for assembly"
        
        # Validate all clips before concatenation
        for i, clip in enumerate(scene_clips):
            if clip is None:
                return None, f"Scene clip {i} is None"
            if not hasattr(clip, 'get_frame'):
                return None, f"Scene clip {i} is not a valid video clip"
                
        final_video_clip = concatenate_videoclips(scene_clips)
        
        # 4. Mix in the background audio
        final_bg_audio_path = background_audio_path or (DEFAULT_BG_AUDIO_PATH if os.path.exists(DEFAULT_BG_AUDIO_PATH) else None)
        if final_bg_audio_path:
            try:
                with AudioFileClip(final_bg_audio_path) as background_clip:
                    background_clip = background_clip.fx(volumex, BACKGROUND_AUDIO_VOLUME).set_duration(final_video_clip.duration)
                    
                    # Check if the main clip has audio
                    if final_video_clip.audio is None:
                        return None, "Main video clip has no audio track"
                    
                    final_video_clip.audio = CompositeAudioClip([final_video_clip.audio, background_clip])
            except Exception as e:
                return None, f"Failed to mix background audio: {e}"

        # 5. Write the final file
        output_dir = "Output_Cartoons"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = random.randint(1000, 9999)
        final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")

        final_video_clip.write_videofile(
            final_video_path, codec='libx264', audio_codec='aac',
            temp_audiofile='temp-audio.m4a', remove_temp=True, fps=FPS, logger=None
        )
        return final_video_path, None

    except subprocess.CalledProcessError as e:
        return None, f"FFMPEG failed.\nSTDERR: {e.stderr}"
    except Exception as e:
        return None, f"An unexpected error occurred during final assembly: {e}"
