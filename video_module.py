# video_module.py
import os
import random
import numpy as np
from PIL import Image
from moviepy.editor import (ImageSequenceClip, AudioFileClip, VideoFileClip, 
                            CompositeVideoClip, concatenate_videoclips, CompositeAudioClip,
                            concatenate_audioclips)
from moviepy.audio.AudioClip import AudioArrayClip # Corrected import location
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

def get_audio_analysis_data(audio_path):
    """
    Analyzes an audio file and returns its duration and a frame-by-frame
    list of which mouth shape to use.
    """
    if not audio_path or not os.path.exists(audio_path):
        return 1.5, ["closed"] * int(1.5 * FPS), None

    try:
        with AudioFileClip(audio_path) as audio_clip:
            duration = audio_clip.duration
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
            
            return duration, mouth_shapes, None
    except Exception as e:
        return None, None, f"Error analyzing audio clip {audio_path}: {e}"

def generate_scene_frames(base_image_np, mouth_pils, mouth_shapes_list, transform_params, frame_dir):
    """Generates and saves each frame for a scene to disk."""
    scale_factor, rotation_angle, position_center = transform_params
    for i, mouth_shape_name in enumerate(mouth_shapes_list):
        frame_pil = Image.fromarray(base_image_np)
        mouth_pil = mouth_pils[mouth_shape_name]
        
        transformed_mouth = mouth_pil.resize((int(mouth_pil.width * scale_factor), int(mouth_pil.height * scale_factor)), Image.Resampling.LANCZOS)
        transformed_mouth = transformed_mouth.rotate(rotation_angle, expand=True, resample=Image.BICUBIC)
        
        mouth_w, mouth_h = transformed_mouth.size
        paste_pos = (int(position_center[0] - mouth_w / 2), int(position_center[1] - mouth_h / 2))
        
        frame_pil.paste(transformed_mouth, paste_pos, transformed_mouth)
        frame_pil.save(os.path.join(frame_dir, f"frame_{i:04d}.png"))

def create_video_from_frames(frame_dir, output_path, audio_path):
    """Uses ffmpeg to create a video from a directory of image frames and attach audio."""
    silent_video_path = os.path.join(os.path.dirname(output_path), "silent_temp.mp4")
    video_command = [
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", os.path.join(frame_dir, "frame_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", silent_video_path
    ]
    subprocess.run(video_command, check=True, capture_output=True, text=True)

    if audio_path and os.path.exists(audio_path):
        audio_command = [
            "ffmpeg", "-y", "-i", silent_video_path, "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-shortest", output_path
        ]
        subprocess.run(audio_command, check=True, capture_output=True, text=True)
    else:
        shutil.move(silent_video_path, output_path)

def create_video_from_script(script_text, audio_paths_dict, background_audio_path=None):
    """Generates a full cartoon video using a highly memory-efficient, ffmpeg-centric approach."""
    temp_dir = tempfile.mkdtemp()
    scene_file_paths = []
    previous_character = None

    try:
        lines = script_text.strip().split('\n')
        for i, line in enumerate(lines):
            char, action, direction_override, dialogue = cgm.parse_script_line(line)
            if not char: continue
            
            audio_path = audio_paths_dict.get(i)
            duration, mouth_shapes, error = get_audio_analysis_data(audio_path)
            if error: return None, error
            
            direction = direction_override or cgm.determine_logical_direction(char.lower(), previous_character)
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
            transform_params = (scale, angle, center)

            mouth_pils = {name: Image.open(find_mouth_shape_path(char, name)[0]).convert("RGBA") for name in set(mouth_shapes)}

            scene_frame_dir = os.path.join(temp_dir, f"scene_{i}_frames")
            os.makedirs(scene_frame_dir, exist_ok=True)
            
            generate_scene_frames(base_image_np, mouth_pils, mouth_shapes, transform_params, scene_frame_dir)
            
            scene_video_path = os.path.join(temp_dir, f"scene_{i}.mp4")
            create_video_from_frames(scene_frame_dir, scene_video_path, audio_path)
            scene_file_paths.append(scene_video_path)
            
            previous_character = char.lower()

        files_to_concatenate = []
        if os.path.exists(OPENING_SEQUENCE_PATH):
            files_to_concatenate.append(OPENING_SEQUENCE_PATH)
        files_to_concatenate.extend(scene_file_paths)

        concat_list_path = os.path.join(temp_dir, "concat.txt")
        with open(concat_list_path, "w") as f:
            for path in files_to_concatenate:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        video_with_dialogue_path = os.path.join(temp_dir, "video_with_dialogue.mp4")
        ffmpeg_command = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", video_with_dialogue_path]
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        
        video_clip = VideoFileClip(video_with_dialogue_path)
        
        final_bg_audio_path = background_audio_path or (DEFAULT_BG_AUDIO_PATH if os.path.exists(DEFAULT_BG_AUDIO_PATH) else None)
        if final_bg_audio_path:
            with AudioFileClip(final_bg_audio_path) as background_clip:
                background_clip = background_clip.fx(volumex, BACKGROUND_AUDIO_VOLUME).set_duration(video_clip.duration)
                if video_clip.audio:
                    video_clip.audio = CompositeAudioClip([video_clip.audio, background_clip])
                else:
                    video_clip.audio = background_clip

        output_dir = "Output_Cartoons"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = random.randint(1000, 9999)
        final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")

        video_clip.write_videofile(
            final_video_path, codec='libx264', audio_codec='aac',
            temp_audiofile='temp-audio.m4a', remove_temp=True, fps=FPS, logger=None
        )
        return final_video_path, None

    except subprocess.CalledProcessError as e:
        return None, f"FFMPEG failed.\nSTDERR: {e.stderr}"
    except Exception as e:
        return None, f"An unexpected error occurred during video creation: {e}"
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
