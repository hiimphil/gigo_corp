# ui_cartoon_generator.py
import streamlit as st
import os
import comic_generator_module
import elevenlabs_module as tts_module
import video_module

def display_cartoon_generator():
    """Renders the cartoon generation workflow UI."""
    st.header("🎬 Cartoon Generation")
    tabs = st.tabs(["Step 1: Generate Audio", "Step 2: Generate Video"])

    with tabs[0]:
        display_audio_tab()

    with tabs[1]:
        display_video_tab()

def display_audio_tab():
    """Renders the UI for the audio generation tab."""
    st.subheader("🎤 Generate Audio for Script")
    if not st.session_state.get('current_script', '').strip():
        st.info("Write a script first.")
        return

    if st.button("Generate All Audio from Text", use_container_width=True):
        st.session_state.final_cartoon_path = None
        audio_paths = {}
        lines = st.session_state.current_script.strip().split('\n')
        with st.spinner("Generating audio for each line..."):
            for i, line in enumerate(lines):
                char, _, _, dialogue = comic_generator_module.parse_script_line(line)
                if char and dialogue:
                    path, error = tts_module.generate_speech_for_line(char, dialogue)
                    if error:
                        st.error(f"Audio failed: {error}")
                        audio_paths = {}
                        break
                    audio_paths[i] = path
                else:
                    audio_paths[i] = None
            st.session_state.generated_audio_paths = audio_paths
            if audio_paths:
                st.success("Audio generated!")
                st.rerun()
    
    st.write("---")
    st.markdown("#### Individual Line Control")
    lines = st.session_state.current_script.strip().split('\n')
    
    for i, line in enumerate(lines):
        with st.container(border=True):
            st.write(f"**Line {i+1}:** *{line.strip()}*")
            if path := st.session_state.generated_audio_paths.get(i):
                st.audio(path)
            else:
                st.info("_(No audio generated yet)_")
            
            char, _, _, dialogue = comic_generator_module.parse_script_line(line)
            if dialogue:
                if st.button("Regenerate Audio", key=f"regen_text_{i}", use_container_width=True):
                    with st.spinner(f"Regenerating audio for line {i+1}..."):
                        new_path, error = tts_module.generate_speech_for_line(char, dialogue)
                        if error:
                            st.error(f"Failed: {error}")
                        else:
                            st.session_state.generated_audio_paths[i] = new_path
                            st.success("Audio updated!")
                            st.rerun()

def display_video_tab():
    """Renders the UI for the video generation tab."""
    st.subheader("📽️ Assemble Final Cartoon")
    st.session_state.background_audio = st.file_uploader(
        "Upload a background audio track (optional)", type=['mp3', 'wav', 'm4a']
    )
    
    if not st.session_state.get('generated_audio_paths'):
        st.info("Generate audio in Step 1 before creating the video.")
        return

    if st.button("Generate Cartoon Video", use_container_width=True, type="primary"):
        bg_audio_path = None
        if st.session_state.background_audio:
            # Save the uploaded file to a temporary location
            temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            bg_audio_path = os.path.join(temp_dir, st.session_state.background_audio.name)
            with open(bg_audio_path, "wb") as f:
                f.write(st.session_state.background_audio.getbuffer())

        with st.spinner("Assembling cartoon... This can take a minute!"):
            video_path, error = video_module.create_video_from_script(
                st.session_state.current_script, 
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
