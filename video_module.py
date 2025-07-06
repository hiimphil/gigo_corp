# video_module.py
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
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
from textwrap import TextWrapper

# --- Configuration ---
FPS = 12
STANDARD_WIDTH = cgm.PANEL_WIDTH
STANDARD_HEIGHT = cgm.PANEL_HEIGHT
BACKGROUND_AUDIO_VOLUME = 0.5

# --- Text Overlay Configuration (matching comic styling) ---
TEXT_FONT = cgm.MAIN_FONT_PATH  # "Fonts/Krungthep.ttf"
TEXT_FONT_SIZE = cgm.FONT_SIZE  # 64
TEXT_COLOR = 'white'
TEXT_POSITION_Y = cgm.TEXT_POSITION_Y  # 500
TEXT_WRAP_WIDTH = cgm.TEXT_WRAP_WIDTH  # 26
TEXT_SPACING = cgm.SPACING_BETWEEN_LINES  # 8

# --- Default Asset Paths ---
DEFAULT_BG_AUDIO_PATH = "SFX/buzz.mp3"
OPENING_SEQUENCE_PATH = "Video/OpeningSequence.mp4"
CARTOON_IMAGE_BASE_PATH = "Cartoon_Images/"

# --- Tracking Dot Configuration ---
LEFT_DOT_COLOR = np.array([0, 255, 0])  # Pure Green
RIGHT_DOT_COLOR = np.array([0, 0, 255]) # Pure Blue

def create_text_overlay_image(dialogue):
    """
    Creates a text overlay image using PIL (same as comic generator).
    This is more reliable than MoviePy's TextClip in cloud environments.
    
    Args:
        dialogue (str): The dialogue text to display
    
    Returns:
        PIL.Image: Transparent image with text overlay
    """
    if not dialogue or not dialogue.strip():
        return None
    
    # Remove action cues from dialogue (text in parentheses)
    import re
    clean_dialogue = re.sub(r'\(.*?\)', '', dialogue).strip()
    if not clean_dialogue:
        return None
    
    # Create transparent image matching video dimensions
    text_image = Image.new('RGBA', (STANDARD_WIDTH, STANDARD_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_image)
    
    # Load font with fallback (same approach as comic generator)
    try:
        font = ImageFont.truetype(TEXT_FONT, TEXT_FONT_SIZE)
    except (IOError, OSError):
        try:
            # Try common system fonts
            font = ImageFont.truetype("Arial.ttf", TEXT_FONT_SIZE)
        except (IOError, OSError):
            # Fallback to default font
            font = ImageFont.load_default()
            print("Warning: Using default font for text overlay")
    
    # Wrap text to match comic layout
    wrapper = TextWrapper(width=TEXT_WRAP_WIDTH)
    lines = wrapper.wrap(text=clean_dialogue)
    
    # Calculate text positioning (same as comic generator)
    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    total_text_block_height = (len(lines) * line_height) + (max(0, len(lines) - 1) * TEXT_SPACING)
    y_text = TEXT_POSITION_Y - total_text_block_height
    
    # Draw each line of text
    for line in lines:
        line_bbox = font.getbbox(line)
        x_text = (STANDARD_WIDTH - (line_bbox[2] - line_bbox[0])) / 2
        draw.text((x_text, y_text), line, font=font, fill=TEXT_COLOR)
        y_text += line_height + TEXT_SPACING
    
    return text_image
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

def find_motion_sequence(character, direction, action):
    """
    Finds motion sequence images for a character. Returns either:
    - List of motion frame paths (for animated sequences)
    - Single base image path (for static scenes)
    """
    base_dir = os.path.join(CARTOON_IMAGE_BASE_PATH, character, direction, action)
    fallback_dir = os.path.join(CARTOON_IMAGE_BASE_PATH, character, direction, "normal")
    
    # Try the specific action directory first
    dirs_to_check = [base_dir, fallback_dir]
    
    for directory in dirs_to_check:
        if not os.path.exists(directory):
            continue
            
        try:
            files = os.listdir(directory)
            
            # Look for numbered motion sequences: base_01.png, base_02.png, etc.
            motion_files = []
            for filename in files:
                if filename.lower().startswith('base_') and filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    # Extract number from filename like "base_01.png"
                    try:
                        num_part = filename.split('_')[1].split('.')[0]
                        frame_num = int(num_part)
                        motion_files.append((frame_num, os.path.join(directory, filename)))
                    except (ValueError, IndexError):
                        continue
            
            # If we found numbered motion files, return them sorted by number
            if motion_files:
                motion_files.sort(key=lambda x: x[0])  # Sort by frame number
                return [path for _, path in motion_files], None
            
            # Otherwise, look for single base.png (current static system)
            base_path = os.path.join(directory, "base.png")
            if os.path.exists(base_path):
                return [base_path], None  # Return as single-item list for consistency
                
        except Exception as e:
            print(f"Error reading directory {directory}: {e}")
            continue
    
    return None, f"No motion sequence or base image found for {character}/{direction}/{action} or normal."

def find_base_image_path(character, direction, action):
    """Legacy function - finds single base image (for backward compatibility)."""
    motion_sequence, error = find_motion_sequence(character, direction, action)
    if error:
        return None, error
    # Return just the first image for backward compatibility
    return motion_sequence[0], None

def find_mouth_shape_path(character, mouth_shape):
    """Finds the path to a specific mouth shape for a character."""
    path = os.path.join(CARTOON_IMAGE_BASE_PATH, character, "mouths", f"{mouth_shape}.png")
    if os.path.exists(path):
        return path, None
    return None, f"Mouth shape '{mouth_shape}' not found for character '{character}'"

def get_motion_sequence_for_scene(motion_paths, duration):
    """
    Generates a frame-by-frame list of motion image paths for a scene.
    Cycles through the motion sequence at a comfortable pace.
    """
    total_frames = int(duration * FPS)
    
    if len(motion_paths) == 1:
        # Static image - use the same image for all frames
        return [motion_paths[0]] * total_frames
    
    # For motion sequences, cycle through at a reasonable pace
    # Default: complete one motion cycle every 2 seconds (24 frames at 12 FPS)
    motion_cycle_frames = max(24, len(motion_paths) * 2)  # At least 2 frames per motion image
    
    motion_sequence = []
    for i in range(total_frames):
        # Calculate which motion frame to use
        cycle_position = i % motion_cycle_frames
        motion_index = int((cycle_position / motion_cycle_frames) * len(motion_paths))
        motion_index = min(motion_index, len(motion_paths) - 1)  # Ensure we don't exceed bounds
        motion_sequence.append(motion_paths[motion_index])
    
    return motion_sequence

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
def render_single_scene(line, audio_path, duration, scene_index, caption_override=None):
    """Generates a single, self-contained video clip for one line of the script with motion support."""
    temp_dir = tempfile.mkdtemp()
    try:
        char, action, direction_override, _, _ = cgm.parse_script_line(line)
        if not char: return None, "Could not parse line."

        # Get mouth animation sequence
        mouth_shapes, error = get_mouth_shapes_for_scene(audio_path, duration)
        if error: return None, error
        
        # Get motion sequence (new!)
        direction = direction_override or cgm.determine_logical_direction(char.lower(), None)
        motion_paths, error = find_motion_sequence(char, direction, action)
        if error: return None, error
        
        # Generate motion sequence for this scene duration
        motion_sequence = get_motion_sequence_for_scene(motion_paths, duration)
        
        # Pre-load all unique motion frames and find their tracking dots
        motion_frames_data = {}
        for motion_path in set(motion_sequence):  # Use set to avoid loading duplicates
            motion_image_pil = Image.open(motion_path).convert("RGB")
            w, h = motion_image_pil.size
            if w % 2 != 0: w -= 1
            if h % 2 != 0: h -= 1
            motion_image_pil = motion_image_pil.crop((0, 0, w, h))
            motion_image_np = np.array(motion_image_pil)
            
            # Find tracking dots for this motion frame
            left_dot, right_dot = find_tracking_dots(motion_image_np)
            if not left_dot or not right_dot: 
                return None, f"Tracking dots not found in {motion_path}"
            
            # Calculate mouth positioning data for this motion frame
            dx, dy = right_dot[0] - left_dot[0], right_dot[1] - left_dot[1]
            scale = math.sqrt(dx**2 + dy**2) / REFERENCE_DOT_DISTANCE
            angle = -math.degrees(math.atan2(dy, dx))
            center = ((left_dot[0] + right_dot[0]) / 2, (left_dot[1] + right_dot[1]) / 2)
            
            motion_frames_data[motion_path] = {
                'image_np': motion_image_np,
                'scale': scale,
                'angle': angle,
                'center': center
            }
        
        # Pre-load all mouth shapes
        unique_mouth_shapes = set(mouth_shapes)
        mouth_pils = {}
        for mouth_shape in unique_mouth_shapes:
            mouth_path, error = find_mouth_shape_path(char, mouth_shape)
            if error: return None, error
            mouth_pils[mouth_shape] = Image.open(mouth_path).convert("RGBA")

        # Generate final frames with dual animation (motion + mouth)
        final_frames = []
        total_frames = len(mouth_shapes)
        
        for frame_index in range(total_frames):
            # Get the motion frame for this time
            current_motion_path = motion_sequence[frame_index]
            motion_data = motion_frames_data[current_motion_path]
            
            # Get the mouth shape for this time
            current_mouth_shape = mouth_shapes[frame_index]
            
            # Start with the motion frame
            frame_pil = Image.fromarray(motion_data['image_np'])
            
            # Apply mouth overlay with positioning data from this motion frame
            mouth_pil = mouth_pils[current_mouth_shape]
            transformed_mouth = mouth_pil.resize(
                (int(mouth_pil.width * motion_data['scale']), 
                 int(mouth_pil.height * motion_data['scale'])), 
                Image.Resampling.LANCZOS
            )
            transformed_mouth = transformed_mouth.rotate(
                motion_data['angle'], expand=True, resample=Image.BICUBIC
            )
            
            mouth_w, mouth_h = transformed_mouth.size
            paste_pos = (
                int(motion_data['center'][0] - mouth_w / 2), 
                int(motion_data['center'][1] - mouth_h / 2)
            )
            frame_pil.paste(transformed_mouth, paste_pos, transformed_mouth)
            final_frames.append(np.array(frame_pil))

        if not final_frames:
            return None, "Failed to generate any frames for the scene."

        # --- Add text overlay if dialogue exists ---
        char, action, direction_override, dialogue, custom_duration = cgm.parse_script_line(line)
        if dialogue:
            # Use caption override if provided, otherwise use original dialogue
            caption_text = caption_override if caption_override is not None else dialogue
            text_overlay_image = create_text_overlay_image(caption_text)
            if text_overlay_image:
                # Composite text onto each frame
                final_frames_with_text = []
                for frame in final_frames:
                    # Convert frame to PIL for compositing
                    frame_pil = Image.fromarray(frame).convert('RGBA')
                    # Composite text overlay
                    frame_with_text = Image.alpha_composite(frame_pil, text_overlay_image)
                    # Convert back to RGB numpy array
                    final_frames_with_text.append(np.array(frame_with_text.convert('RGB')))
                
                final_frames = final_frames_with_text

        # Create the video clip from the frames (with or without text)
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

    except Exception as e:
        return None, f"Unexpected error in scene generation: {e}"
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        # Clean up local variables to free memory
        if 'final_frames' in locals():
            del final_frames
        if 'final_frames_with_text' in locals():
            del final_frames_with_text
        if 'video_clip' in locals():
            try:
                video_clip.close()
            except:
                pass
        if 'dialogue_clip' in locals():
            try:
                dialogue_clip.close()
            except:
                pass
        if 'silent_audio' in locals():
            try:
                silent_audio.close()
            except:
                pass
        
        # Force garbage collection
        import gc
        gc.collect()

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
        # Choose assembly method based on scene count
        if len(scene_paths) <= 10:
            st.write(f"  Using MoviePy for {len(scene_paths)} scenes...")
            # Continue with original MoviePy approach below
        else:
            st.write(f"  Using batch MoviePy assembly for {len(scene_paths)} scenes...")
            return assemble_with_batch_moviepy(scene_paths, background_audio_path)
        
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

# FFmpeg function removed - using batch MoviePy for all large cartoons

def assemble_with_batch_moviepy(scene_paths, background_audio_path=None):
    """
    Memory-efficient video assembly using MoviePy in batches.
    Maintains MoviePy quality while handling large scene counts.
    """
    import streamlit as st
    import tempfile
    
    try:
        st.write(f"  Processing {len(scene_paths)} scenes in batches...")
        
        # Configuration
        BATCH_SIZE = 8  # Process 8 scenes per batch for optimal memory usage
        temp_dir = tempfile.mkdtemp()
        batch_files = []
        
        # Split scenes into batches
        for batch_start in range(0, len(scene_paths), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(scene_paths))
            batch_scenes = scene_paths[batch_start:batch_end]
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = (len(scene_paths) + BATCH_SIZE - 1) // BATCH_SIZE
            
            st.write(f"  Processing batch {batch_num}/{total_batches} (scenes {batch_start+1}-{batch_end})...")
            
            # Load scenes for this batch
            batch_clips = []
            try:
                for i, path in enumerate(batch_scenes):
                    if not os.path.exists(path):
                        raise Exception(f"Scene file not found: {path}")
                    clip = VideoFileClip(path)
                    if clip is None:
                        raise Exception(f"Failed to load scene: {path}")
                    batch_clips.append(clip)
                
                # Concatenate this batch
                batch_video = concatenate_videoclips(batch_clips)
                
                # Save batch to temporary file
                batch_filename = f"batch_{batch_num:03d}.mp4"
                batch_path = os.path.join(temp_dir, batch_filename)
                
                st.write(f"    Rendering batch {batch_num}...")
                batch_video.write_videofile(
                    batch_path,
                    codec='libx264',
                    audio_codec='aac',
                    fps=FPS,
                    preset='medium',
                    ffmpeg_params=['-crf', '23'],
                    logger=None,
                    verbose=False
                )
                
                batch_files.append(batch_path)
                st.write(f"    ✅ Batch {batch_num} completed ({batch_video.duration:.1f}s)")
                
                # Clean up batch clips to free memory
                batch_video.close()
                for clip in batch_clips:
                    clip.close()
                del batch_clips, batch_video
                
            except Exception as e:
                # Clean up on error
                for clip in batch_clips:
                    try:
                        clip.close()
                    except:
                        pass
                raise Exception(f"Error processing batch {batch_num}: {e}")
        
        st.write(f"  All {total_batches} batches completed. Assembling final video...")
        
        # Now assemble all batch files plus opening sequence
        final_clips = []
        
        # Add opening sequence if it exists
        if os.path.exists(OPENING_SEQUENCE_PATH):
            try:
                st.write(f"  Adding opening sequence...")
                opening_clip = VideoFileClip(OPENING_SEQUENCE_PATH)
                if opening_clip.size == [STANDARD_WIDTH, STANDARD_HEIGHT]:
                    final_clips.append(opening_clip)
                else:
                    st.warning(f"Skipping opening sequence: size mismatch")
                    opening_clip.close()
            except Exception as e:
                st.warning(f"Skipping opening sequence: {e}")
        
        # Add all batch files
        for batch_path in batch_files:
            batch_clip = VideoFileClip(batch_path)
            final_clips.append(batch_clip)
        
        # Concatenate all final clips
        st.write(f"  Concatenating {len(final_clips)} segments...")
        final_video = concatenate_videoclips(final_clips)
        
        # Handle background audio
        if background_audio_path and os.path.exists(background_audio_path):
            try:
                st.write(f"  Adding background audio...")
                background_clip = AudioFileClip(background_audio_path)
                background_clip = background_clip.fx(volumex, BACKGROUND_AUDIO_VOLUME)
                
                if background_clip.duration < final_video.duration:
                    background_clip = background_clip.loop(duration=final_video.duration)
                else:
                    background_clip = background_clip.subclip(0, final_video.duration)
                
                if final_video.audio is None:
                    final_video = final_video.set_audio(background_clip)
                else:
                    composite_audio = CompositeAudioClip([final_video.audio, background_clip])
                    final_video = final_video.set_audio(composite_audio)
                
                st.write(f"  ✅ Background audio mixed successfully")
            except Exception as e:
                st.warning(f"Background audio mixing failed: {e}. Continuing without background audio...")
        
        # Write final video
        output_dir = "Output_Cartoons"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = random.randint(1000, 9999)
        final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")
        
        st.write(f"  🎬 Rendering final cartoon... This may take a moment.")
        final_video.write_videofile(
            final_video_path,
            codec='libx264',
            audio_codec='aac',
            fps=FPS,
            preset='medium',
            ffmpeg_params=['-crf', '23'],
            logger=None,
            verbose=False
        )
        
        st.write(f"  ✅ Batch assembly completed! Final duration: {final_video.duration:.1f}s")
        st.write(f"  Saved as: {os.path.basename(final_video_path)}")
        
        return final_video_path, None
        
    except Exception as e:
        return None, f"Batch MoviePy assembly failed: {e}"
    
    finally:
        # Clean up all resources
        try:
            if 'final_clips' in locals():
                for clip in final_clips:
                    try:
                        clip.close()
                    except:
                        pass
            if 'final_video' in locals():
                try:
                    final_video.close()
                except:
                    pass
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass
