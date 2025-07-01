# ui_cartoon_maker.py
import streamlit as st
import time
import os
import re 
import comic_generator_module # We can reuse some parsing logic
import ai_script_module
import database_module
import elevenlabs_module as tts_module
import video_module

def _init_cartoon_keys():
    """A safeguard function to ensure all cartoon-related keys exist in session state."""
    if 'cartoon_script' not in st.session_state: st.session_state.cartoon_script = ""
    if 'cartoon_title' not in st.session_state: st.session_state.cartoon_title = "My First Cartoon"
    if 'generated_audio_paths' not in st.session_state: st.session_state.generated_audio_paths = {}
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
        help="Write a script between 4 and 12 lines. Use brackets for performance notes, e.g., A: [shouting] I need coffee!"
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
    tabs = st.tabs(["Step 1: Generate Audio", "Step 2: Generate Video"])

    script_to_use = st.session_state.get('cartoon_script', '')

    with tabs[0]:
        display_audio_tab(script_to_use)

    with tabs[1]:
        display_video_tab(script_to_use)

def display_audio_tab(script):
    """Renders the UI for the audio generation tab."""
    st.subheader("🎤 Generate Audio for Script")
    if not script.strip():
        st.info("Write a cartoon script first.")
        return

    if st.button("Generate All Audio", use_container_width=True, key="gen_all_cartoon_audio"):
        st.session_state.final_cartoon_path = None
        audio_paths = {}
        lines = script.strip().split('\n') # Use the passed 'script' variable
        with st.spinner("Generating audio for each line..."):
            for i, line in enumerate(lines):
                char, _, _, dialogue = comic_generator_module.parse_script_line(line)
                if char and dialogue:
                    # --- NEW LOGIC: Only strip out parenthetical visual cues ---
                    # This regular expression removes only the content in parentheses ()
                    spoken_dialogue = re.sub(r'\(.*?\)', '', dialogue).strip()
                    
                    path, error = tts_module.generate_speech_for_line(char, spoken_dialogue)
                    if error:
                        st.error(f"Audio failed: {error}"); audio_paths = {}; break
                    audio_paths[i] = path
                else:
                    audio_paths[i] = None
            st.session_state.generated_audio_paths = audio_paths
            if audio_paths:
                st.success("Audio generated!")
                st.rerun()
    
    if st.session_state.get('generated_audio_paths'):
        st.write("---")
        lines = script.strip().split('\n') # Use the passed 'script' variable
        for i, line in enumerate(lines):
            with st.container(border=True):
                st.write(f"**Line {i+1}:** *{line.strip()}*")
                if path := st.session_state.generated_audio_paths.get(i):
                    st.audio(path)
                else:
                    st.info("_(No audio generated yet)_")
                
                char, _, _, dialogue = comic_generator_module.parse_script_line(line)
                if dialogue:
                    if st.button("Regenerate Audio", key=f"regen_cartoon_audio_{i}", use_container_width=True):
                        with st.spinner(f"Regenerating audio for line {i+1}..."):
                            # --- NEW LOGIC: Also apply for regeneration ---
                            spoken_dialogue = re.sub(r'\(.*?\)', '', dialogue).strip()
                            new_path, error = tts_module.generate_speech_for_line(char, spoken_dialogue)
                            if error:
                                st.error(f"Failed: {error}")
                            else:
                                st.session_state.generated_audio_paths[i] = new_path
                                st.success("Audio updated!")
                                st.rerun()

def display_video_tab(script):
    """Renders the UI for the video generation tab."""
    st.subheader("📽️ Assemble Final Cartoon")
    st.session_state.background_audio = st.file_uploader(
        "Upload a background audio track (optional)", type=['mp3', 'wav', 'm4a'], key="cartoon_bg_audio"
    )
    
    if not st.session_state.get('generated_audio_paths'):
        st.info("Generate audio in Step 1 before creating the video.")
        return

    if st.button("Generate Cartoon Video", use_container_width=True, type="primary", key="gen_cartoon_video"):
        bg_audio_path = None
        if st.session_state.background_audio:
            temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            bg_audio_path = os.path.join(temp_dir, st.session_state.background_audio.name)
            with open(bg_audio_path, "wb") as f:
                f.write(st.session_state.background_audio.getbuffer())

        with st.spinner("Assembling cartoon... This can take a minute!"):
            video_path, error = video_module.create_video_from_script(
                script, # Use the passed 'script' variable
                st.session_state.generated_audio_paths,
                bg_audio_path
            )
            if error:
                st.error(f"Video Failed: {error}")
            else:
                st.session_state.final_cartoon_path = video_path
                st.rerun()

    if st.session_state.get('final_cartoon_path'):
        st.success("Cartoon generated successfully!")
        st.video(st.session_state.final_cartoon_path)
