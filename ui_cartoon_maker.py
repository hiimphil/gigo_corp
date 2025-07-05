# ui_cartoon_maker.py
import streamlit as st
import time
import os
import re 
import comic_generator_module 
import ai_script_module
import database_module
import elevenlabs_module as tts_module
import video_module
from moviepy.editor import AudioFileClip # Import for getting duration

def _init_cartoon_keys():
    """A safeguard function to ensure all cartoon-related keys exist in session state."""
    if 'cartoon_script' not in st.session_state: st.session_state.cartoon_script = ""
    if 'cartoon_title' not in st.session_state: st.session_state.cartoon_title = "My First Cartoon"
    if 'generated_audio_paths' not in st.session_state: st.session_state.generated_audio_paths = {}
    if 'generated_audio_durations' not in st.session_state: st.session_state.generated_audio_durations = {} # New state for durations
    if 'generated_scene_paths' not in st.session_state: st.session_state.generated_scene_paths = {}
    if 'final_cartoon_path' not in st.session_state: st.session_state.final_cartoon_path = None
    if 'background_audio' not in st.session_state: st.session_state.background_audio = None

def display(is_admin):
    """Renders the entire UI for the new Cartoon Maker workflow."""
    _init_cartoon_keys()

    st.header("Cartoon Maker")
    st.write("Create a short, animated Gigo Corp cartoon with dialogue and background audio.")
    st.divider()

    # --- Script Library for Cartoons ---
    st.subheader("📜 Cartoon Script Library")
    cartoon_scripts = database_module.load_scripts("cartoon_scripts")
    if cartoon_scripts:
        script_to_load = st.selectbox(
            "Select a cartoon script:", 
            options=list(cartoon_scripts.keys()), 
            index=None, 
            placeholder="-- Choose a script to load --",
            key="cartoon_script_selectbox"
        )
        load_col, delete_col = st.columns(2)
        with load_col:
            if st.button("Load Cartoon Script", use_container_width=True):
                if script_to_load:
                    st.session_state.cartoon_script = cartoon_scripts[script_to_load]
                    st.session_state.cartoon_title = script_to_load
                    st.rerun()
        with delete_col:
            if st.button("Delete Cartoon Script", use_container_width=True):
                if script_to_load and is_admin:
                    database_module.delete_script(script_to_load, "cartoon_scripts")
                    st.toast(f"Deleted '{script_to_load}'")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("No cartoon scripts saved yet.")
    st.divider()

    # --- Cartoon Script Editor ---
    st.subheader("📝 Cartoon Script Editor")
    st.session_state.cartoon_title = st.text_input("Cartoon Title:", value=st.session_state.get('cartoon_title', ''))
    st.session_state.cartoon_script = st.text_area(
        "Cartoon Script (4-12 lines)", 
        value=st.session_state.get('cartoon_script', ''), 
        height=250,
        help="Use (visual notes) and [performance notes]. e.g., A: [shouting] I need coffee!"
    )

    # --- Action Buttons for Cartoon Script ---
    cs_col1, cs_col2 = st.columns(2)
    with cs_col1:
        if st.button("💾 Save Cartoon Script", use_container_width=True):
            if is_admin:
                database_module.save_script(st.session_state.cartoon_title, st.session_state.cartoon_script, "cartoon_scripts")
                st.toast("Cartoon script saved!")
            else:
                st.warning("Admin access required.")
    with cs_col2:
        if st.button("🤖 Generate or Complete Cartoon Script", use_container_width=True):
            with st.spinner("AI is drafting a longer script..."):
                new_script = ai_script_module.generate_cartoon_script(partial_script=st.session_state.cartoon_script)
                if new_script and not new_script.startswith("Error:"):
                    st.session_state.cartoon_script = new_script
                    st.rerun()
                else:
                    st.error(f"AI Failed: {new_script}")
    
    st.divider()

    # --- Cartoon Generation UI ---
    display_cartoon_generator()


def display_cartoon_generator():
    """Renders the cartoon generation workflow UI with horizontal storyboard layout."""
    st.header("🎬 Cartoon Generation")
    
    script_to_use = st.session_state.get('cartoon_script', '')
    
    if not script_to_use.strip():
        st.info("Write a cartoon script first.")
        return
    
    # Parse script into lines for storyboard
    lines = script_to_use.strip().split('\n')
    
    # Display horizontal storyboard
    display_horizontal_storyboard(lines)

def display_horizontal_storyboard(lines):
    """Renders a horizontal storyboard with columns for each scene."""
    st.subheader("🎭 Storyboard")
    
    # Global controls
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🎤 Generate All Audio", use_container_width=True):
            generate_all_audio(lines)
    with col2:
        if st.button("🎬 Generate All Scenes", use_container_width=True):
            generate_all_scenes(lines)
    with col3:
        if st.button("🎯 Assemble Final Cartoon", use_container_width=True):
            assemble_final_cartoon_ui(lines)
    
    st.write("---")
    
    # Create storyboard using native Streamlit layout
    # Show 2 scenes per row for better readability
    scenes_per_row = 2
    
    for row_start in range(0, len(lines), scenes_per_row):
        row_end = min(row_start + scenes_per_row, len(lines))
        row_lines = lines[row_start:row_end]
        
        if len(row_lines) == 1:
            # Single column for one scene - center it
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                display_scene_column(row_start, row_lines[0])
        else:
            # Multiple columns for this row
            cols = st.columns(len(row_lines))
            for i, line in enumerate(row_lines):
                scene_index = row_start + i
                with cols[i]:
                    display_scene_column(scene_index, line)
        
        # Add spacing between rows (only if not the last row)
        if row_end < len(lines):
            st.markdown("<br>", unsafe_allow_html=True)
    
    # Show final cartoon if assembled
    if st.session_state.get('final_cartoon_path'):
        st.write("---")
        st.subheader("🎉 Final Cartoon")
        st.video(st.session_state.final_cartoon_path)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            with open(st.session_state.final_cartoon_path, "rb") as file:
                st.download_button(
                    label="📥 Download Final Cartoon",
                    data=file.read(),
                    file_name=os.path.basename(st.session_state.final_cartoon_path),
                    mime="video/mp4",
                    use_container_width=True
                )
        with col2:
            if st.button("🗑️ Clear Final Cartoon", use_container_width=True):
                st.session_state.final_cartoon_path = None
                st.rerun()

def display_scene_column(scene_index, line):
    """Renders a single scene column in the storyboard."""
    with st.container(border=True):
        # Parse the line to get character, dialogue, and duration
        char, action, direction_override, dialogue, duration = comic_generator_module.parse_script_line(line)
        
        # Header: Scene number, character name, and action
        char_name = {"a": "Artie", "b": "B00L", "c": "Cling", "d": "Dusty"}.get(char, char.upper() if char else "Unknown")
        action_display = action.capitalize() if action else "Normal"
        if duration:
            header_text = f"**Scene {scene_index + 1}   {char_name}   {action_display}   ({duration}s)**"
        else:
            header_text = f"**Scene {scene_index + 1}   {char_name}   {action_display}**"
        st.write(header_text)
        
        # 1. Visual Section (top)
        # Show scene video if generated, otherwise placeholder
        if scene_index in st.session_state.get('generated_scene_paths', {}):
            scene_path = st.session_state.generated_scene_paths[scene_index]
            if scene_path and os.path.exists(scene_path):
                st.video(scene_path)
                if st.button("🔄 Regenerate Scene", key=f"regen_scene_{scene_index}", use_container_width=True):
                    generate_single_scene(scene_index, line)
            else:
                st.image("https://via.placeholder.com/300x200?text=Scene+Not+Generated", width=250)
        else:
            # Show character preview image
            if char:
                # Get and display the actual character image
                try:
                    preview_image_path = get_character_preview_image(char, action, direction_override)
                    
                    if preview_image_path and isinstance(preview_image_path, str) and os.path.exists(preview_image_path):
                        st.image(preview_image_path, width=250)
                    else:
                        st.image("https://via.placeholder.com/300x200?text=Click+to+Generate", width=250)
                except Exception as e:
                    st.image("https://via.placeholder.com/300x200?text=Preview+Error", width=250)
            else:
                st.image("https://via.placeholder.com/300x200?text=No+Character", width=250)
        
        # 2. Script Line Section (middle) - editable
        edited_line = st.text_area("", value=line, height=70, key=f"script_line_{scene_index}")
        if edited_line != line:
            # Update the script in session state
            lines = st.session_state.cartoon_script.strip().split('\n')
            lines[scene_index] = edited_line
            st.session_state.cartoon_script = '\n'.join(lines)
            st.rerun()
        
        # 3. Audio Section (bottom)
        # Show audio player if generated
        audio_generated = scene_index in st.session_state.get('generated_audio_paths', {})
        
        if audio_generated:
            audio_path = st.session_state.generated_audio_paths[scene_index]
            if audio_path and os.path.exists(audio_path):
                st.audio(audio_path)
                
                # Show status
                status = st.session_state.get('audio_generation_status', {}).get(scene_index, 'unknown')
                if status == "cached":
                    st.caption("☁️ From cache")
                elif status == "generated":
                    st.caption("✨ Newly generated")
                
                if st.button("🔄 Regenerate Audio", key=f"regen_audio_{scene_index}", use_container_width=True):
                    regenerate_single_audio(scene_index, edited_line)
            else:
                st.info("Audio not found")
                if dialogue and st.button("🎤 Generate Audio", key=f"gen_audio_{scene_index}", use_container_width=True):
                    generate_single_audio(scene_index, edited_line)
        else:
            if dialogue:
                if st.button("🎤 Generate Audio", key=f"gen_audio_{scene_index}", use_container_width=True):
                    generate_single_audio(scene_index, edited_line)
            else:
                if duration:
                    st.info(f"Silent scene ({duration}s)")
                else:
                    st.info("Silent scene (default duration)")
        
        # 4. Scene Generation Button (only enabled if audio is generated or it's a silent scene)
        scene_ready = audio_generated or not dialogue  # Ready if audio exists or it's silent
        if scene_ready:
            if st.button("🎬 Generate Scene", key=f"gen_scene_bottom_{scene_index}", use_container_width=True):
                generate_single_scene(scene_index, edited_line)
        else:
            st.button("🎬 Generate Scene", key=f"gen_scene_disabled_{scene_index}", use_container_width=True, disabled=True, help="Generate audio first")

# Helper functions for storyboard actions
def get_character_preview_image(char, action, direction_override=None):
    """Get the character's base image for preview in storyboard using Cartoon_Images folder."""
    try:
        if not char:
            return None
        
        # Ensure action is valid
        if not action:
            action = "normal"
        
        # Use Cartoon_Images directory structure
        cartoon_images_base = "Cartoon_Images/"
        
        # Determine direction
        if direction_override:
            direction = direction_override
        else:
            direction = comic_generator_module.determine_logical_direction(char, None)
        
        # Build path based on Cartoon_Images structure: Cartoon_Images/character/direction/action/
        # Try different combinations to find an image
        paths_to_try = [
            os.path.join(cartoon_images_base, char, direction, action),
            os.path.join(cartoon_images_base, char, direction, "normal"),
            os.path.join(cartoon_images_base, char, "straight", action),
            os.path.join(cartoon_images_base, char, "straight", "normal"),
        ]
        
        for path in paths_to_try:
            if os.path.isdir(path):
                try:
                    images = [f for f in os.listdir(path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    if images:
                        return os.path.join(path, images[0])  # Return first image found
                except Exception as e:
                    print(f"Could not read directory '{path}': {e}")
                    continue
        
        print(f"No image found in Cartoon_Images for {char}/{direction}/{action}")
        return None
            
    except Exception as e:
        print(f"Error getting preview image for {char}: {e}")
        return None

def generate_single_audio(scene_index, line):
    """Generate audio for a single scene."""
    char, _, _, dialogue, _ = comic_generator_module.parse_script_line(line)
    if char and dialogue:
        with st.spinner(f"Generating audio for scene {scene_index + 1}..."):
            spoken_dialogue = re.sub(r'\(.*?\)', '', dialogue).strip()
            path, error, status = tts_module.generate_speech_for_line(char, spoken_dialogue)
            if error:
                st.error(f"Audio failed: {error}")
            else:
                st.session_state.generated_audio_paths[scene_index] = path
                st.session_state.audio_generation_status[scene_index] = status or "generated"
                with AudioFileClip(path) as clip:
                    st.session_state.generated_audio_durations[scene_index] = clip.duration
                st.success(f"Audio generated for scene {scene_index + 1}!")
                st.rerun()

def regenerate_single_audio(scene_index, line):
    """Regenerate audio for a single scene."""
    char, _, _, dialogue, _ = comic_generator_module.parse_script_line(line)
    if char and dialogue:
        with st.spinner(f"Regenerating audio for scene {scene_index + 1}..."):
            spoken_dialogue = re.sub(r'\(.*?\)', '', dialogue).strip()
            path, error, status = tts_module.generate_speech_for_line(char, spoken_dialogue, force_regenerate=True)
            if error:
                st.error(f"Audio failed: {error}")
            else:
                st.session_state.generated_audio_paths[scene_index] = path
                st.session_state.audio_generation_status[scene_index] = status or "generated"
                with AudioFileClip(path) as clip:
                    st.session_state.generated_audio_durations[scene_index] = clip.duration
                st.success(f"Audio regenerated for scene {scene_index + 1}!")
                st.rerun()

def generate_single_scene(scene_index, line):
    """Generate video for a single scene."""
    with st.spinner(f"Generating scene {scene_index + 1}..."):
        # Parse line to get custom duration if specified
        char, _, _, dialogue, custom_duration = comic_generator_module.parse_script_line(line)
        
        audio_path = st.session_state.get('generated_audio_paths', {}).get(scene_index)
        
        # Use custom duration if specified, otherwise use audio duration or default
        if custom_duration:
            duration = custom_duration
        else:
            duration = st.session_state.get('generated_audio_durations', {}).get(scene_index, 3.0)
        
        scene_path, error = video_module.render_single_scene(line, audio_path, duration, scene_index)
        if error:
            st.error(f"Scene generation failed: {error}")
        else:
            st.session_state.generated_scene_paths[scene_index] = scene_path
            st.success(f"Scene {scene_index + 1} generated!")
            st.rerun()

def generate_all_audio(lines):
    """Generate audio for all scenes."""
    st.session_state.final_cartoon_path = None
    st.session_state.generated_scene_paths = {}
    
    with st.spinner("Generating audio for all scenes..."):
        for i, line in enumerate(lines):
            char, _, _, dialogue, custom_duration = comic_generator_module.parse_script_line(line)
            if char and dialogue:
                spoken_dialogue = re.sub(r'\(.*?\)', '', dialogue).strip()
                path, error, status = tts_module.generate_speech_for_line(char, spoken_dialogue)
                if error:
                    st.error(f"Audio failed for scene {i+1}: {error}")
                    return
                st.session_state.generated_audio_paths[i] = path
                st.session_state.audio_generation_status[i] = status or "generated"
                with AudioFileClip(path) as clip:
                    st.session_state.generated_audio_durations[i] = clip.duration
            else:
                st.session_state.generated_audio_paths[i] = None
                # Use custom duration if specified, otherwise default
                st.session_state.generated_audio_durations[i] = custom_duration or 1.5
        
        st.success("All audio generated!")
        st.rerun()

def generate_all_scenes(lines):
    """Generate video for all scenes sequentially with progress tracking."""
    import gc
    import time
    
    # Create a progress container
    progress_container = st.container()
    
    with progress_container:
        st.write("🎬 **Generating All Scenes**")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, line in enumerate(lines):
            # Update progress
            progress = (i) / len(lines)
            progress_bar.progress(progress)
            status_text.write(f"Processing scene {i+1} of {len(lines)}...")
            
            # Parse line to get custom duration if specified
            char, _, _, dialogue, custom_duration = comic_generator_module.parse_script_line(line)
            
            audio_path = st.session_state.get('generated_audio_paths', {}).get(i)
            
            # Use custom duration if specified, otherwise use audio duration or default
            if custom_duration:
                duration = custom_duration
            else:
                duration = st.session_state.get('generated_audio_durations', {}).get(i, 3.0)
            
            # Generate the scene
            scene_path, error = video_module.render_single_scene(line, audio_path, duration, i)
            if error:
                st.error(f"Scene {i+1} generation failed: {error}")
                progress_bar.empty()
                status_text.empty()
                return
            
            # Store the result
            st.session_state.generated_scene_paths[i] = scene_path
            
            # Force garbage collection to free memory between scenes
            gc.collect()
            
            # Brief pause to allow UI to update and memory to clear
            time.sleep(0.1)
        
        # Final progress update
        progress_bar.progress(1.0)
        status_text.write("✅ All scenes generated successfully!")
        
        # Clean up progress indicators after a moment
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        st.success("All scenes generated!")
        st.rerun()

def assemble_final_cartoon_ui(lines):
    """Assemble the final cartoon from all scenes."""
    # Check if all scenes are generated
    missing_scenes = []
    for i in range(len(lines)):
        if i not in st.session_state.get('generated_scene_paths', {}) or not st.session_state.generated_scene_paths[i]:
            missing_scenes.append(i + 1)
    
    if missing_scenes:
        st.error(f"Missing scenes: {', '.join(map(str, missing_scenes))}. Generate all scenes first.")
        return
    
    # Get background audio if uploaded
    bg_audio_path = None
    if st.session_state.get('background_audio'):
        import tempfile
        temp_dir = tempfile.mkdtemp()
        bg_audio_path = os.path.join(temp_dir, st.session_state.background_audio.name)
        with open(bg_audio_path, "wb") as f:
            f.write(st.session_state.background_audio.getbuffer())
    
    with st.spinner("Assembling final cartoon..."):
        ordered_scene_paths = [st.session_state.generated_scene_paths[i] for i in range(len(lines))]
        final_path, error = video_module.assemble_final_cartoon(ordered_scene_paths, bg_audio_path)
        
        if error:
            st.error(f"Final assembly failed: {error}")
        else:
            st.session_state.final_cartoon_path = final_path
            st.success("Final cartoon assembled!")
            st.rerun()

def display_audio_tab(script):
    """Renders the UI for the audio generation tab."""
    st.subheader("🎤 Generate Audio for Script")
    if not script.strip():
        st.info("Write a cartoon script first.")
        return

    if st.button("Generate All Audio", use_container_width=True, key="gen_all_cartoon_audio"):
        st.session_state.final_cartoon_path = None
        st.session_state.generated_scene_paths = {} # Clear old scenes
        audio_paths = {}
        audio_durations = {}
        lines = script.strip().split('\n')
        with st.spinner("Generating audio for each line..."):
            for i, line in enumerate(lines):
                char, _, _, dialogue = comic_generator_module.parse_script_line(line)
                if char and dialogue:
                    spoken_dialogue = re.sub(r'\(.*?\)', '', dialogue).strip()
                    path, error, status = tts_module.generate_speech_for_line(char, spoken_dialogue)
                    if error:
                        st.error(f"Audio failed: {error}"); audio_paths = {}; break
                    audio_paths[i] = path
                    # Set status from the actual function return
                    st.session_state.audio_generation_status[i] = status or "generated"
                    # Get and store the duration immediately
                    with AudioFileClip(path) as clip:
                        audio_durations[i] = clip.duration
                else:
                    audio_paths[i] = None
                    audio_durations[i] = 1.5 # Default pause duration
            st.session_state.generated_audio_paths = audio_paths
            st.session_state.generated_audio_durations = audio_durations
            if audio_paths:
                st.success("Audio generated!")
                # Add the rerun call back to refresh the UI
                st.rerun()
    
    if st.session_state.get('generated_audio_paths'):
        st.write("---")
        lines = script.strip().split('\n')
        for i, line in enumerate(lines):
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**Line {i+1}:** *{line.strip()}*")
                    if path := st.session_state.generated_audio_paths.get(i):
                        st.audio(path)
                    else:
                        st.info("_(No audio generated yet)_")
                
                with col2:
                    # Display the status icon based on the session state
                    status = st.session_state.audio_generation_status.get(i)
                    if status == "cached":
                        st.markdown("☁️ _From cache_")
                    elif status == "generated":
                        st.markdown("✨ _Newly generated_")

                char, _, _, dialogue = comic_generator_module.parse_script_line(line)
                if dialogue:
                    if st.button("Regenerate Audio", key=f"regen_cartoon_audio_{i}", use_container_width=True):
                        with st.spinner(f"Regenerating audio for line {i+1}..."):
                            spoken_dialogue = re.sub(r'\(.*?\)', '', dialogue).strip()
                            new_path, error, status = tts_module.generate_speech_for_line(char, spoken_dialogue, force_regenerate=True)
                            if error:
                                st.error(f"Failed: {error}")
                            else:
                                st.session_state.generated_audio_paths[i] = new_path
                                st.session_state.audio_generation_status[i] = status or "generated"
                                # Update the duration as well
                                with AudioFileClip(new_path) as clip:
                                    st.session_state.generated_audio_durations[i] = clip.duration
                                st.success("Audio updated!")
                                st.rerun()

def display_storyboard_tab(script):
    """Renders the UI for the scene-by-scene video generation and final assembly."""
    st.subheader("📽️ Storyboard & Assembly")
    
    if not st.session_state.get('generated_audio_paths'):
        st.info("Generate audio in Step 1 before creating the storyboard.")
        return

    lines = script.strip().split('\n')
    
    # Display the storyboard
    for i, line in enumerate(lines):
        with st.container(border=True):
            st.write(f"**Scene {i+1}:** *{line.strip()}*")
            
            scene_path = st.session_state.generated_scene_paths.get(i)
            if scene_path and os.path.exists(scene_path):
                st.video(scene_path)
            else:
                if st.button("Generate Scene", key=f"gen_scene_{i}"):
                    with st.spinner(f"Generating scene {i+1}..."):
                        path, error = video_module.render_single_scene(
                            line, 
                            st.session_state.generated_audio_paths.get(i),
                            st.session_state.generated_audio_durations.get(i, 1.5), # Pass the duration
                            i
                        )
                        if error:
                            st.error(f"Scene generation failed: {error}")
                        else:
                            st.session_state.generated_scene_paths[i] = path
                            st.rerun()
    
    st.divider()
    st.subheader("Assemble Final Cartoon")
    
    # Check if all scenes have been generated
    all_scenes_generated = len(st.session_state.generated_scene_paths) == len(lines)
    
    if not all_scenes_generated:
        st.warning("Please generate all scenes before assembling the final cartoon.")
    else:
        st.session_state.background_audio = st.file_uploader(
            "Upload a background audio track (optional)", type=['mp3', 'wav', 'm4a'], key="cartoon_bg_audio"
        )
        
        if st.button("Assemble & Render Final Cartoon", use_container_width=True, type="primary"):
            bg_audio_path = None
            if st.session_state.background_audio:
                temp_dir = "temp"
                os.makedirs(temp_dir, exist_ok=True)
                bg_audio_path = os.path.join(temp_dir, st.session_state.background_audio.name)
                with open(bg_audio_path, "wb") as f:
                    f.write(st.session_state.background_audio.getbuffer())

            with st.spinner("Assembling final cartoon... This may take a moment."):
                # Create a list of scene paths in the correct order
                ordered_scene_paths = []
                for i in range(len(lines)):
                    if i in st.session_state.generated_scene_paths:
                        scene_path = st.session_state.generated_scene_paths[i]
                        if scene_path and os.path.exists(scene_path):
                            ordered_scene_paths.append(scene_path)
                        else:
                            st.error(f"Scene {i} path is missing or invalid: {scene_path}")
                            return
                    else:
                        st.error(f"Scene {i} was not generated")
                        return
                
                if not ordered_scene_paths:
                    st.error("No valid scene paths found for assembly")
                    return
                
                final_path, error = video_module.assemble_final_cartoon(ordered_scene_paths, bg_audio_path)
                if error:
                    st.error(f"Final assembly failed: {error}")
                else:
                    st.session_state.final_cartoon_path = final_path
                    st.rerun()

    if st.session_state.get('final_cartoon_path'):
        st.success("Final cartoon generated successfully!")
        st.video(st.session_state.final_cartoon_path)
