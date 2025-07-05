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
        char, action, direction_override, _, _ = cgm.parse_script_line(line)
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
        video_clip.write_videofile(
            scene_video_path, 
            codec='libx264', 
            audio_codec='aac', 
            fps=FPS, 
            preset='medium',
            ffmpeg_params=['-crf', '23', '-vsync', 'cfr'],
            logger=None
        )

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
        # Assembly info
        import streamlit as st
        st.write(f"🎬 Assembling {len(scene_paths)} scenes into final cartoon...")
        # --- SIMPLIFIED ASSEMBLY PROCESS ---
        # 1. Memory-efficient approach: Choose best method based on scene count
        # For large numbers of scenes, use FFmpeg directly for better memory efficiency
        if len(scene_paths) > 10:
            st.write(f"  Using FFmpeg for efficient processing...")
            return assemble_with_ffmpeg(scene_paths, background_audio_path)
        else:
            st.write(f"  Using MoviePy for {len(scene_paths)} scenes...")
        
        # For smaller numbers, use MoviePy but with careful memory management
        scene_clips = []
        for i, path in enumerate(scene_paths):
            if not os.path.exists(path):
                # Clean up any loaded clips before returning error
                for clip in scene_clips:
                    clip.close()
                return None, f"Scene {i} file not found: {path}"
            try:
                st.write(f"  Loading scene {i+1}/{len(scene_paths)}...")
                clip = VideoFileClip(path)
                if clip is None:
                    # Clean up before returning error
                    for existing_clip in scene_clips:
                        existing_clip.close()
                    return None, f"Scene {i} failed to load: {path}"
                scene_clips.append(clip)
            except Exception as e:
                # Clean up any loaded clips before returning error
                for existing_clip in scene_clips:
                    existing_clip.close()
                return None, f"Error loading scene {i} ({path}): {e}"
        
        # 2. Prepend the opening sequence
        if os.path.exists(OPENING_SEQUENCE_PATH):
            try:
                st.write(f"  Adding opening sequence...")
                opening_clip = VideoFileClip(OPENING_SEQUENCE_PATH)
                if opening_clip.size != [STANDARD_WIDTH, STANDARD_HEIGHT]:
                     return None, f"OpeningSequence.mp4 is not {STANDARD_WIDTH}x{STANDARD_HEIGHT}."
                scene_clips.insert(0, opening_clip)
            except Exception as e:
                return None, f"Failed to load opening sequence: {e}"

        # 3. Validate and concatenate all video clips
        if not scene_clips:
            return None, "No valid scene clips found for assembly"
        
        st.write(f"  Concatenating {len(scene_clips)} clips...")
        # Validate all clips before concatenation
        for i, clip in enumerate(scene_clips):
            if clip is None:
                return None, f"Scene clip {i} is None"
            if not hasattr(clip, 'get_frame'):
                return None, f"Scene clip {i} is not a valid video clip"
                
        final_video_clip = concatenate_videoclips(scene_clips)
        st.write(f"  ✅ Concatenation complete! Final duration: {final_video_clip.duration:.1f}s")
        
        # 4. Mix in the background audio (safer approach)
        final_bg_audio_path = background_audio_path or (DEFAULT_BG_AUDIO_PATH if os.path.exists(DEFAULT_BG_AUDIO_PATH) else None)
        if final_bg_audio_path:
            try:
                st.write(f"  Adding background audio...")
                background_clip = AudioFileClip(final_bg_audio_path)
                
                # Adjust background audio volume and loop/trim to match video duration
                background_clip = background_clip.fx(volumex, BACKGROUND_AUDIO_VOLUME)
                if background_clip.duration < final_video_clip.duration:
                    background_clip = background_clip.loop(duration=final_video_clip.duration)
                else:
                    background_clip = background_clip.subclip(0, final_video_clip.duration)
                
                # Check if the main clip has audio
                if final_video_clip.audio is None:
                    final_video_clip = final_video_clip.set_audio(background_clip)
                else:
                    composite_audio = CompositeAudioClip([final_video_clip.audio, background_clip])
                    final_video_clip = final_video_clip.set_audio(composite_audio)
                
                st.write(f"  ✅ Background audio mixed successfully")
            except Exception as e:
                st.warning(f"Background audio mixing failed: {e}. Continuing without background audio...")
        

        # 5. Write the final file
        output_dir = "Output_Cartoons"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = random.randint(1000, 9999)
        final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")

        # Validate final clip before writing
        if final_video_clip is None:
            return None, "Final video clip is None"
        if not hasattr(final_video_clip, 'get_frame'):
            return None, "Final video clip has no get_frame method"
        
        st.write(f"  🎬 Rendering final video... This may take a moment.")
        final_video_clip.write_videofile(
            final_video_path, codec='libx264', audio_codec='aac',
            temp_audiofile='temp-audio.m4a', remove_temp=True, fps=FPS, logger=None
        )
        st.write(f"  ✅ Final cartoon completed! Saved as: {os.path.basename(final_video_path)}")
        return final_video_path, None

    except subprocess.CalledProcessError as e:
        return None, f"FFMPEG failed.\nSTDERR: {e.stderr}"
    except Exception as e:
        return None, f"An unexpected error occurred during final assembly: {e}"
    finally:
        # Clean up all loaded clips to free memory
        if 'scene_clips' in locals():
            for clip in scene_clips:
                try:
                    clip.close()
                except:
                    pass
        if 'opening_clip' in locals():
            try:
                opening_clip.close()
            except:
                pass
        if 'final_video_clip' in locals():
            try:
                final_video_clip.close()
            except:
                pass

def assemble_with_ffmpeg(scene_paths, background_audio_path=None):
    """
    Memory-efficient video assembly using FFmpeg directly.
    Better for large numbers of scenes.
    """
    import streamlit as st
    
    try:
        st.write(f"  Using FFmpeg for efficient assembly of {len(scene_paths)} scenes...")
        
        # Create output directory
        output_dir = "Output_Cartoons"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = random.randint(1000, 9999)
        final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")
        
        # Create temporary file list for FFmpeg concat
        temp_dir = tempfile.mkdtemp()
        concat_file = os.path.join(temp_dir, "concat_list.txt")
        
        # Build the concat file content
        concat_content = []
        
        # Add opening sequence if it exists (but validate it first)
        if os.path.exists(OPENING_SEQUENCE_PATH):
            try:
                # Check if opening sequence properties match our scenes
                opening_clip = VideoFileClip(OPENING_SEQUENCE_PATH)
                if opening_clip.size == [STANDARD_WIDTH, STANDARD_HEIGHT]:
                    concat_content.append(f"file '{os.path.abspath(OPENING_SEQUENCE_PATH)}'")
                    st.write(f"  Adding opening sequence...")
                else:
                    st.warning(f"Skipping opening sequence: size mismatch ({opening_clip.size} vs [{STANDARD_WIDTH}, {STANDARD_HEIGHT}])")
                opening_clip.close()
            except Exception as e:
                st.warning(f"Skipping opening sequence due to error: {e}")
        
        # Add all scene files
        for path in scene_paths:
            abs_path = os.path.abspath(path)
            concat_content.append(f"file '{abs_path}'")
        
        # Write concat file
        with open(concat_file, 'w') as f:
            f.write('\n'.join(concat_content))
        
        st.write(f"  Concatenating {len(scene_paths)} scenes with FFmpeg...")
        
        # Validate scene files have consistent properties
        st.write(f"  Validating scene consistency...")
        try:
            # Quick check of first scene to get expected properties
            first_clip = VideoFileClip(scene_paths[0])
            expected_fps = first_clip.fps
            expected_size = first_clip.size
            first_clip.close()
            
            st.write(f"  Expected properties: {expected_size[0]}x{expected_size[1]} @ {expected_fps}fps")
        except Exception as e:
            st.warning(f"Could not validate scene properties: {e}")
        
        # Build FFmpeg command with proper re-encoding to fix sync issues
        ffmpeg_cmd = [
            'ffmpeg', '-y',  # -y to overwrite output file
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c:v', 'libx264',  # Re-encode video to ensure consistency
            '-c:a', 'aac',      # Re-encode audio to ensure consistency
            '-r', str(FPS),     # Force consistent frame rate
            '-vsync', 'cfr',    # Constant frame rate (fixes timing issues)
            '-preset', 'medium', # Good quality/speed balance
            '-crf', '23',       # Good quality setting
            final_video_path
        ]
        
        # Run FFmpeg
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return None, f"FFmpeg concatenation failed: {result.stderr}"
        
        # Handle background audio if provided
        if background_audio_path and os.path.exists(background_audio_path):
            st.write(f"  Adding background audio...")
            temp_video = final_video_path + "_temp.mp4"
            os.rename(final_video_path, temp_video)
            
            # Mix background audio with existing audio
            audio_cmd = [
                'ffmpeg', '-y',
                '-i', temp_video,
                '-i', background_audio_path,
                '-filter_complex', f'[1:a]volume={BACKGROUND_AUDIO_VOLUME}[bg];[0:a][bg]amix=inputs=2[out]',
                '-map', '0:v',
                '-map', '[out]',
                '-c:v', 'copy',
                '-c:a', 'aac',
                final_video_path
            ]
            
            audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
            
            # Clean up temp file
            if os.path.exists(temp_video):
                os.remove(temp_video)
            
            if audio_result.returncode != 0:
                st.warning(f"Background audio mixing failed, continuing without: {audio_result.stderr}")
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        st.write(f"  ✅ FFmpeg assembly completed successfully!")
        st.write(f"  Note: Video has been re-encoded to fix sync issues - this ensures proper playback.")
        return final_video_path, None
        
    except Exception as e:
        return None, f"FFmpeg assembly failed: {e}"
    finally:
        # Clean up temp directory if it exists
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
