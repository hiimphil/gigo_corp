# video_module.py
import os
import random
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
    # Use the existing comic generator's robust pathfinding logic.
    # We pass the case-insensitive, lowercase versions of the inputs.
    base_path, _ = cgm.find_image_path(character.lower(), talking_state.lower(), direction.lower(), action.lower())

    if not base_path:
        return []

    # The find_image_path function returns a path to a single file.
    # We want the directory that contains that file.
    image_dir = os.path.dirname(base_path)

    if os.path.isdir(image_dir):
        # Get all image files in the directory and sort them alphabetically.
        # This ensures animations like 'talk_01.png', 'talk_02.png' play in order.
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
    # Determine the character's state (talking or not talking)
    talking_state = "talking" if dialogue else "nottalking"
    
    # For now, we'll use the logical direction. This can be expanded later.
    direction = cgm.determine_logical_direction(character.lower(), None) # Simplified for now
    
    # Find the visual assets for the scene
    frame_paths = find_animation_frames(character, talking_state, direction, action)
    
    if not frame_paths:
        # If no images are found, we can't create a clip.
        return None, f"Could not find any images for {character} in state {talking_state}/{action}"

    # Get the duration from the audio file. If no audio, it's a silent pause.
    if audio_path and os.path.exists(audio_path):
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
    else:
        # If there's no dialogue, create a default pause of 1.5 seconds.
        duration = 1.5
        audio_clip = None

    # --- Create the image sequence ---
    num_frames_in_sequence = len(frame_paths)
    total_frames_in_clip = int(duration * FPS)
    
    final_frame_list = []
    if num_frames_in_sequence == 1:
        # If it's a static image, just repeat it for the whole duration.
        final_frame_list = [frame_paths[0]] * total_frames_in_clip
    else:
        # If it's an animation, loop through the frames.
        for i in range(total_frames_in_clip):
            # The modulo operator (%) creates a repeating cycle.
            frame_index = i % num_frames_in_sequence
            final_frame_list.append(frame_paths[frame_index])

    # --- Assemble the video clip with MoviePy ---
    if not final_frame_list:
        return None, "Failed to generate frame list for the scene."

    # Create the video from the list of image paths
    video_clip = ImageSequenceClip(final_frame_list, fps=FPS)

    # Assign the audio to the video clip
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

    # Combine all the individual scene clips into one final video
    final_video = concatenate_videoclips(scene_clips)
    
    # Define a path for the final output video
    output_dir = "Output_Cartoons"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = random.randint(1000, 9999) # Simple timestamp
    final_video_path = os.path.join(output_dir, f"gigoco_cartoon_{timestamp}.mp4")

    # Write the final video file to disk
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
