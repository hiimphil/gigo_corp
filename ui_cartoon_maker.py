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
    """Renders the cartoon generation workflow UI, adapted for the cartoon script."""
    st.header("🎬 Cartoon Generation")
    tabs = st.tabs(["Step 1: Generate Audio", "Step 2: Storyboard & Assembly"])

    script_to_use = st.session_state.get('cartoon_script', '')

    with tabs[0]:
        display_audio_tab(script_to_use)

    with tabs[1]:
        display_storyboard_tab(script_to_use)

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
                    path, error, _ = tts_module.generate_speech_for_line(char, spoken_dialogue)
                    if error:
                        st.error(f"Audio failed: {error}"); audio_paths = {}; break
                    audio_paths[i] = path
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
                            new_path, error, _ = tts_module.generate_speech_for_line(char, spoken_dialogue, force_regenerate=True)
                            if error:
                                st.error(f"Failed: {error}")
                            else:
                                st.session_state.generated_audio_paths[i] = new_path
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
                ordered_scene_paths = [st.session_state.generated_scene_paths[i] for i in range(len(lines))]
                
                final_path, error = video_module.assemble_final_cartoon(ordered_scene_paths, bg_audio_path)
                if error:
                    st.error(f"Final assembly failed: {error}")
                else:
                    st.session_state.final_cartoon_path = final_path
                    st.rerun()

    if st.session_state.get('final_cartoon_path'):
        st.success("Final cartoon generated successfully!")
        st.video(st.session_state.final_cartoon_path)
