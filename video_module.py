# video_module.py
import os
import random
import numpy as np
from PIL import Image
from moviepy.editor import (AudioFileClip, VideoFileClip, 
                            CompositeAudioClip, concatenate_videoclips)
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

    if left_dot_coords[0].size == 0 or right_dot_coords[0].size == 0: return None, None
    left_pos = (left_dot_coords[1][0], left_dot_coords[0][0])
    right_pos = (right_dot_coords[1][0], right_dot_coords[0][0])
    return left_pos, right_pos

def find_base_image_path(character, direction, action):
    """Finds the path to the mouthless base image for a character."""
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, direction, action, "base.png")
    if os.path.exists(path): return path, None
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, direction, "normal", "base.png")
    if os.path.exists(path): return path, None
    return None, f"No base image found for {character}/{direction}/{action} or normal."

def find_mouth_shape_path(character, mouth_shape):
    """Finds the path to a specific mouth shape for a character."""
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, "mouths", f"{mouth_shape}.png")
    if os.path.exists(path): return path, None
    return None, f"Mouth shape '{mouth_shape}' not found for character '{character}'"

def get_audio_analysis_data(audio_path):
    """
    Analyzes an audio file and returns its duration and a frame-by-frame
    list of which mouth shape to use.
    """
    if not audio_path or not os.path.exists(audio_path):
        return 1.5, ["closed"] * int(1.5 * FPS)
    try:
        with AudioFileClip(audio_path) as audio_clip:
            duration = audio_clip.duration
            total_frames = int(duration * FPS)
            mouth_shapes = []
            for i in range(total_frames):
                current_time = float(i) / FPS
                sample = audio_clip.get_frame(current_time)
                if sample.ndim > 1: sample = sample.mean(axis=1)
                volume = np.max(np.abs(sample))
                if volume < SILENCE_THRESHOLD: mouth_shapes.append("closed")
                elif volume < SMALL_MOUTH_THRESHOLD: mouth_shapes.append("open-small")
                else: mouth_shapes.append("open-large")
            return duration, mouth_shapes
    except Exception as e:
        return None, f"Error analyzing audio clip {audio_path}: {e}"

# --- NEW: Scene Rendering Function ---
def render_single_scene(line, audio_path, scene_index):
    """
    Generates a single, self-contained video clip for one line of the script.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        char, action, direction_override, _ = cgm.parse_script_line(line)
        if not char: return None, "Could not parse line."

        duration, mouth_shapes = get_audio_analysis_data(audio_path)
        if isinstance(mouth_shapes, str): return None, mouth_shapes # Error message
        
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

        frame_dir = os.path.join(temp_dir, "frames")
        os.makedirs(frame_dir, exist_ok=True)

        for i, mouth_shape_name in enumerate(mouth_shapes):
            frame_pil = Image.fromarray(base_image_np)
            mouth_pil = mouth_pils[mouth_shape_name]
            transformed_mouth = mouth_pil.resize((int(mouth_pil.width * scale), int(mouth_pil.height * scale)), Image.Resampling.LANCZOS)
            transformed_mouth = transformed_mouth.rotate(angle, expand=True, resample=Image.BICUBIC)
            mouth_w, mouth_h = transformed_mouth.size
            paste_pos = (int(center[0] - mouth_w / 2), int(center[1] - mouth_h / 2))
            frame_pil.paste(transformed_mouth, paste_pos, transformed_mouth)
            frame_pil.save(os.path.join(frame_dir, f"frame_{i:04d}.png"))

        # Use ffmpeg to create the scene video with audio
        output_dir = "Output_Scenes"
        os.makedirs(output_dir, exist_ok=True)
        scene_video_path = os.path.join(output_dir, f"scene_{scene_index}.mp4")
        
        silent_video_path = os.path.join(temp_dir, "silent.mp4")
        video_command = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(frame_dir, "frame_%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", silent_video_path]
        subprocess.run(video_command, check=True, capture_output=True, text=True)

        if audio_path:
            audio_command = ["ffmpeg", "-y", "-i", silent_video_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", scene_video_path]
            subprocess.run(audio_command, check=True, capture_output=True, text=True)
        else:
            shutil.copy(silent_video_path, scene_video_path)

        return scene_video_path, None

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# --- NEW: Final Assembly Function ---
def assemble_final_cartoon(scene_paths, background_audio_path=None):
    """
    Assembles pre-rendered scene clips into a final cartoon.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        files_to_concatenate = []
        if os.path.exists(OPENING_SEQUENCE_PATH):
            files_to_concatenate.append(OPENING_SEQUENCE_PATH)
        files_to_concatenate.extend(scene_paths)

        concat_list_path = os.path.join(temp_dir, "concat.txt")
        with open(concat_list_path, "w") as f:
            for path in files_to_concatenate:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        video_with_dialogue_path = os.path.join(temp_dir, "video_with_dialogue.mp4")
        ffmpeg_command = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", video_with_dialogue_path]
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        
        final_video_clip = VideoFileClip(video_with_dialogue_path)
        
        final_bg_audio_path = background_audio_path or (DEFAULT_BG_AUDIO_PATH if os.path.exists(DEFAULT_BG_AUDIO_PATH) else None)
        if final_bg_audio_path:
            with AudioFileClip(final_bg_audio_path) as background_clip:
                background_clip = background_clip.fx(volumex, BACKGROUND_AUDIO_VOLUME).set_duration(final_video_clip.duration)
                if final_video_clip.audio:
                    final_video_clip.audio = CompositeAudioClip([final_video_clip.audio, background_clip])
                else:
                    final_video_clip.audio = background_clip

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
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
