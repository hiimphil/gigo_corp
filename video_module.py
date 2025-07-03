# video_module.py
import os
import random
import numpy as np
from PIL import Image
from moviepy.editor import (AudioFileClip, VideoFileClip, 
                            CompositeVideoClip, concatenate_videoclips, CompositeAudioClip)
from moviepy.audio.fx.all import volumex
import comic_generator_module as cgm
import math
import tempfile 
import shutil 
import subprocess # New import for running ffmpeg

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

def create_scene_video_from_frames(frame_dir, output_path, duration, audio_path):
    """
    Uses ffmpeg to create a video from a directory of image frames.
    This is highly memory-efficient.
    """
    # Create the video from the image sequence
    video_command = [
        "ffmpeg",
        "-framerate", str(FPS),
        "-i", os.path.join(frame_dir, "frame_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-y", # Overwrite output file if it exists
        output_path
    ]
    subprocess.run(video_command, check=True, capture_output=True, text=True)

    # If there's audio, attach it to the newly created video
    if audio_path:
        final_output_path = output_path.replace(".mp4", "_final.mp4")
        audio_command = [
            "ffmpeg",
            "-i", output_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            "-y",
            final_output_path
        ]
        subprocess.run(audio_command, check=True, capture_output=True, text=True)
        return final_output_path
        
    return output_path


def create_scene_clip_memory_efficient(character, action, direction_override, dialogue, audio_path, prev_char, scene_index, parent_temp_dir):
    """
    Generates all frames for a scene, saves them to disk, and then uses ffmpeg
    to create the final video clip. This is the most memory-efficient method.
    """
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
        mouth_shapes[shape_name] = Image.open(path).convert("RGBA")

    # Create a dedicated directory for this scene's frames
    scene_frame_dir = os.path.join(parent_temp_dir, f"scene_{scene_index}_frames")
    os.makedirs(scene_frame_dir, exist_ok=True)

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
        
        # Save the frame to disk instead of holding it in memory
        frame_pil.save(os.path.join(scene_frame_dir, f"frame_{i:04d}.png"))

    # Now, use ffmpeg to create the video from the saved frames
    scene_video_path = os.path.join(parent_temp_dir, f"scene_{scene_index}.mp4")
    final_scene_path = create_scene_video_from_frames(scene_frame_dir, scene_video_path, duration, audio_path)
    
    return final_scene_path, None


def create_video_from_script(script_text, audio_paths_dict, background_audio_path=None):
    """
    Generates a full cartoon video using the highly memory-efficient, frame-by-frame approach.
    """
    temp_dir = tempfile.mkdtemp()
    scene_file_paths = []
    previous_character = None

    try:
        lines = script_text.strip().split('\n')
        for i, line in enumerate(lines):
            char, action, direction_override, dialogue = cgm.parse_script_line(line)
            if not char: continue
            
            audio_path = audio_paths_dict.get(i)
            # Call the new memory-efficient function
            scene_path, error = create_scene_clip_memory_efficient(char, action, direction_override, dialogue, audio_path, previous_character, i, temp_dir)
            
            if error: return None, error
            if not scene_path: continue
            
            scene_file_paths.append(scene_path)
            previous_character = char.lower()

        if not scene_file_paths:
            return None, "No scenes were generated."

        # Use ffmpeg to concatenate the final scene files
        concat_list_path = os.path.join(temp_dir, "concat.txt")
        with open(concat_list_path, "w") as f:
            for path in scene_file_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        main_body_path = os.path.join(temp_dir, "main_body.mp4")
        ffmpeg_command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            main_body_path
        ]
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        
        main_cartoon_body = VideoFileClip(main_body_path)
        # --- End Memory Fix ---

        final_bg_audio_path = background_audio_path or (DEFAULT_BG_AUDIO_PATH if os.path.exists(DEFAULT_BG_AUDIO_PATH) else None)
        if final_bg_audio_path:
            try:
                background_clip = AudioFileClip(final_bg_audio_path).fx(volumex, BACKGROUND_AUDIO_VOLUME)
                background_clip = background_clip.set_duration(main_cartoon_body.duration)
                if main_cartoon_body.audio:
                    combined_audio = CompositeAudioClip([main_cartoon_body.audio, background_clip])
                    main_cartoon_body.audio = combined_audio
                else:
                    main_cartoon_body.audio = background_clip
            except Exception as e:
                return None, f"Failed to process background audio: {e}"

        final_clips_to_join = []
        if os.path.exists(OPENING_SEQUENCE_PATH):
            try:
                opening_clip = VideoFileClip(OPENING_SEQUENCE_PATH)
                if opening_clip.size != [STANDARD_WIDTH, STANDARD_HEIGHT]:
                     return None, f"OpeningSequence.mp4 is not {STANDARD_WIDTH}x{STANDARD_HEIGHT}."
                final_clips_to_join.append(opening_clip)
            except Exception as e:
                return None, f"Failed to load opening sequence: {e}"

        final_clips_to_join.append(main_cartoon_body)
        final_video = concatenate_videoclips(final_clips_to_join)

        # --- Final Output ---
        output_dir = "Output_Cartoons"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = random.randint(1000, 9999)
        final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")

        final_video.write_videofile(
            final_video_path, codec='libx264', audio_codec='aac',
            temp_audiofile='temp-audio.m4a', remove_temp=True, fps=FPS
        )
        return final_video_path, None

    except subprocess.CalledProcessError as e:
        # Provide detailed ffmpeg error output for debugging
        return None, f"FFMPEG concatenation failed.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"

    except Exception as e:
        return None, f"MoviePy failed during video creation: {e}"
    finally:
        # --- MEMORY FIX: Clean up the temporary directory ---
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
