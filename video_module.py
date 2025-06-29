# video_module.py
import os
import random
from moviepy.editor import ImageClip, ImageSequenceClip, AudioFileClip, concatenate_videoclips
import comic_generator_module as cgm

# --- Configuration ---
FPS = 12  # Frames per second for the animation. 12 is good for a simple cartoon style.
STANDARD_WIDTH = cgm.PANEL_WIDTH   # 512
STANDARD_HEIGHT = cgm.PANEL_HEIGHT # 640

def find_animation_frames(character, talking_state, direction, action):
    """
    Finds a sequence of images for animation.
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


def create_scene_clip(character, action, dialogue, audio_path, prev_char):
    """
    Creates a single video clip for one line of dialogue, now with correct direction
    and robust frame resizing to prevent drifting.
    """
    talking_state = "talking" if dialogue else "nottalking"
    
    # --- DIRECTION FIX ---
    # The direction is now correctly determined using the previous character.
    direction = cgm.determine_logical_direction(character.lower(), prev_char)
    
    frame_paths = find_animation_frames(character, talking_state, direction, action)
    if not frame_paths:
        return None, f"Could not find any images for {character} in state {talking_state}/{action}"

    # Determine scene duration from audio, or a default pause
    if audio_path and os.path.exists(audio_path):
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
    else:
        duration = 1.5
        audio_clip = None

    # --- IMAGE DRIFT FIX ---
    # To prevent drifting, we'll convert every frame to a numpy array of a standard size.
    
    # 1. Load each unique image and resize it into a moviepy ImageClip.
    unique_image_clips = [ImageClip(path).resize(width=STANDARD_WIDTH, height=STANDARD_HEIGHT) for path in frame_paths]

    # 2. Get the raw image data (numpy array) from each resized clip.
    unique_numpy_frames = [clip.get_frame(0) for clip in unique_image_clips]

    # 3. Build the full list of frames for the scene's duration.
    num_unique_frames = len(unique_numpy_frames)
    total_frames_in_scene = int(duration * FPS)
    final_frame_list = []

    if num_unique_frames == 1:
        # If it's a static shot, repeat the single frame.
        final_frame_list = [unique_numpy_frames[0]] * total_frames_in_scene
    else:
        # If it's an animation, loop through the unique frames.
        for i in range(total_frames_in_scene):
            frame_index = i % num_unique_frames
            final_frame_list.append(unique_numpy_frames[frame_index])

    if not final_frame_list:
        return None, "Failed to generate numpy frame list for the scene."

    # Create the video from the list of uniform numpy arrays
    video_clip = ImageSequenceClip(final_frame_list, fps=FPS)

    # Assign audio if it exists
    if audio_clip:
        video_clip = video_clip.set_audio(audio_clip)

    return video_clip, None


def create_video_from_script(script_text, audio_paths_dict):
    """
    Generates a full cartoon video, passing character context for correct direction.
    """
    lines = script_text.strip().split('\n')
    scene_clips = []
    previous_character = None  # Initialize previous character tracker

    for i, line in enumerate(lines):
        char, action, _, dialogue = cgm.parse_script_line(line)
        if not char:
            continue

        audio_path = audio_paths_dict.get(i)
        
        # Pass the previous character to the scene creation function
        scene_clip, error = create_scene_clip(char, action, dialogue, audio_path, previous_character)
        if error:
            return None, error
        
        if scene_clip:
            scene_clips.append(scene_clip)
        
        # Update the tracker for the next iteration
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
