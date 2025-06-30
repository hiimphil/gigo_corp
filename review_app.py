# review_app.py
import os
import time
os.environ['MAGICK_CONFIGURE_PATH'] = '.'

import streamlit as st
from st_audiorec import st_audiorec
import comic_generator_module
import ai_script_module
import social_media_module 
import bluesky_module
import instagram_module
import imgur_uploader
import database_module
import reddit_module
import elevenlabs_module as tts_module
import video_module
from pydub import audio_segment
import io

# --- Session State Initialization ---
def init_session_state():
    if 'current_script' not in st.session_state: st.session_state.current_script = ""
    if 'script_title' not in st.session_state: st.session_state.script_title = "My First Comic"
    if 'preview_image' not in st.session_state: st.session_state.preview_image = None
    if 'generated_comic_paths' not in st.session_state: st.session_state.generated_comic_paths = []
    if 'imgur_image_links' not in st.session_state: st.session_state.imgur_image_links = []
    if 'generated_audio_paths' not in st.session_state: st.session_state.generated_audio_paths = {}
    if 'final_cartoon_path' not in st.session_state: st.session_state.final_cartoon_path = None
    if 'background_audio' not in st.session_state: st.session_state.background_audio = None
    if 'recording_for_line' not in st.session_state: st.session_state.recording_for_line = None

    default_caption = "This comic is property of Gigo Co. #webcomic #gigo"
    if 'instagram_caption' not in st.session_state: st.session_state.instagram_caption = default_caption
    if 'bluesky_caption' not in st.session_state: st.session_state.bluesky_caption = default_caption
    if 'twitter_caption' not in st.session_state: st.session_state.twitter_caption = default_caption
    if 'reddit_title' not in st.session_state: st.session_state.reddit_title = "Gigo Corp Comic"
    if 'reddit_subreddit' not in st.session_state: st.session_state.reddit_subreddit = "GigoCorp"

init_session_state()

# --- Helper Function for Password Check ---
def check_password():
    try:
        password = st.sidebar.text_input("Enter Password for Admin Access", type="password")
        if "APP_PASSWORD" in st.secrets and password == st.secrets.get("APP_PASSWORD"):
            return True
        elif "APP_PASSWORD" not in st.secrets and password == "localpass":
             st.sidebar.info("Using local password. Set APP_PASSWORD secret for deployment.")
             return True
        elif password:
            st.sidebar.warning("Incorrect password.")
            return False
        else:
            return False
    except Exception:
        st.sidebar.info("Password feature disabled. For local dev, you can set a fallback.")
        return True

st.set_page_config(layout="wide")
st.title("Gigo Corp Comic & Cartoon Builder")


# --- Sidebar ---
st.sidebar.header("🔑 Admin Access")
is_admin = check_password()
st.sidebar.divider()
st.sidebar.header("🎨 Action Guide")
st.sidebar.write("Use `(action)` or `(direction)` in a script line.")
st.sidebar.code("A:(left) Hi!\nB:(shocked) Hello.")
available_actions = comic_generator_module.get_available_actions()
if available_actions:
    for char, states in available_actions.items():
        with st.sidebar.expander(f"Character {char.upper()} Actions"):
            for state, directions in states.items():
                st.write(f"**{state.capitalize()}:**")
                for direction, actions in directions.items():
                    if actions:
                        st.write(f"- _{direction.capitalize()}_: {', '.join(actions)}")
else:
    st.sidebar.info("No action folders found in your 'Images' directory.")
st.sidebar.divider()
st.sidebar.header("📜 Script Library")
saved_scripts = database_module.load_scripts() 
if saved_scripts:
    script_to_load = st.sidebar.selectbox("Select a script:", options=list(saved_scripts.keys()), index=None, placeholder="-- Choose a script to load --")
    load_col, delete_col = st.sidebar.columns(2)
    with load_col:
        if st.button("Load Script", use_container_width=True):
            if script_to_load:
                st.session_state.current_script = saved_scripts[script_to_load]
                st.session_state.script_title = script_to_load; st.rerun()
    with delete_col:
        if st.button("Delete", use_container_width=True):
            if script_to_load and is_admin:
                success, message = database_module.delete_script(script_to_load)
                st.toast(message, icon="🗑️" if success else "❌"); time.sleep(1); st.rerun()
            else: st.sidebar.warning("Select a script and be an admin.")
else:
    st.sidebar.write("No saved scripts in Firestore yet.")

def reset_downstream_state():
    st.session_state.preview_image = None
    st.session_state.generated_comic_paths = []
    st.session_state.generated_audio_paths = {}
    st.session_state.final_cartoon_path = None
    st.session_state.imgur_image_links = []


# --- Main Area ---
st.header("📝 Script Editor")
st.session_state.script_title = st.text_input("Script Title:", st.session_state.script_title)
st.session_state.current_script = st.text_area("Comic Script", value=st.session_state.current_script, height=150)

# --- Action Buttons ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("💾 Save Script", use_container_width=True):
        if is_admin:
            success, message = database_module.save_script(st.session_state.script_title, st.session_state.current_script)
            st.toast(message, icon="✅" if success else "❌"); time.sleep(1); st.rerun()
        else: st.warning("You must be an admin to save scripts.")

with col2:
    if st.button("🤖 Generate or Complete Script", use_container_width=True):
        with st.spinner("AI is working..."):
            new_script = ai_script_module.generate_ai_script(partial_script=st.session_state.current_script)
            if new_script and not new_script.startswith("Error:"):
                st.session_state.current_script = new_script
                reset_downstream_state()
                st.rerun()
            else: st.error(f"AI Failed: {new_script}")

with col3:
    if st.button("🖼️ Generate Preview", use_container_width=True):
        reset_downstream_state()
        with st.spinner("Generating preview..."):
            preview, error = comic_generator_module.generate_preview_image(st.session_state.current_script)
            if error: st.error(f"Preview Failed: {error}")
            else: st.session_state.preview_image = preview

if st.session_state.preview_image:
    st.divider()
    st.header("👀 Comic Preview")
    st.image(st.session_state.preview_image, use_container_width=True)
    with col4:
        if st.button("✅ Approve & Finalize Comic", use_container_width=True, type="primary"):
            with st.spinner("Finalizing comic images..."):
                final_paths, error = comic_generator_module.generate_comic_from_script_text(st.session_state.current_script)
                if error: st.error(f"Finalization Failed: {error}")
                else: st.session_state.generated_comic_paths = final_paths; st.success("Final comic files generated!"); st.rerun()
    st.divider()

# --- Cartoon Generation Workflow ---
st.header("🎬 Cartoon Generation")
tabs = st.tabs(["Step 1: Generate Audio", "Step 2: Generate Video"])

with tabs[0]:
    st.subheader("🎤 Generate Audio for Script")
    if not st.session_state.current_script.strip():
        st.info("Write a script first.")
    else:
        if st.button("Generate All Audio from Text", use_container_width=True):
            st.session_state.recording_for_line = None
            st.session_state.final_cartoon_path = None
            audio_paths = {}
            lines = st.session_state.current_script.strip().split('\n')
            with st.spinner("Generating audio for each line..."):
                for i, line in enumerate(lines):
                    char, _, _, dialogue = comic_generator_module.parse_script_line(line)
                    if char and dialogue:
                        path, error = tts_module.generate_speech_for_line(char, dialogue)
                        if error: st.error(f"Audio failed: {error}"); audio_paths = {}; break
                        audio_paths[i] = path
                    else: audio_paths[i] = None
                st.session_state.generated_audio_paths = audio_paths
                if audio_paths: st.success("Audio generated!")

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
                
                # --- New UI for Recording ---
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Regenerate from Text", key=f"regen_text_{i}", use_container_width=True):
                        char, _, _, dialogue = comic_generator_module.parse_script_line(line)
                        if dialogue:
                            with st.spinner(f"Regenerating audio for line {i+1}..."):
                                new_path, error = tts_module.generate_speech_for_line(char, dialogue)
                                if error: st.error(f"Failed: {error}")
                                else:
                                    st.session_state.generated_audio_paths[i] = new_path
                                    st.success("Audio updated!"); st.rerun()
                        else:
                            st.warning("No dialogue to generate.")
                with col2:
                    if st.button("Record Performance", key=f"record_perf_{i}", use_container_width=True, type="secondary"):
                        # Set which line we are recording for and rerun to show the UI
                        st.session_state.recording_for_line = i
                        st.rerun()
        
        # --- Recorder UI (shown outside the loop) ---
        if st.session_state.recording_for_line is not None:
            line_index = st.session_state.recording_for_line
            line_text = lines[line_index]
            char, _, _, _ = comic_generator_module.parse_script_line(line_text)

            with st.container(border=True):
                st.subheader(f"🎙️ Recording for Line {line_index + 1}: {char.upper()}")
                st.write(f"*{line_text.strip()}*")
                
                # The audio recorder is now only called ONCE, solving the duplicate ID error
                wav_audio_data = st_audiorec()

                if wav_audio_data:
                    # This is now the temporary file we will pass to ElevenLabs
                    temp_mp3_path = f"temp_recording_{line_index}.mp3"
                    
                    # --- FINAL AUDIO FIX: Use pydub to convert raw WAV to MP3 ---
                    try:
                        # Load the raw audio data from the recorder
                        audio_segment = AudioSegment.from_file(io.BytesIO(wav_audio_data), format="wav")
                        
                        # Export it as a clean MP3 file, which forces ffmpeg to be used
                        audio_segment.export(temp_mp3_path, format="mp3")

                    except Exception as e:
                        st.error(f"Error processing recorded audio: {e}")
                    # --- END OF FINAL AUDIO FIX ---

                    if st.button("Use This Recording", key=f"use_rec_{line_index}"):
                        with st.spinner(f"Converting your voice to {char.upper()}'s voice..."):
                            # Pass the path to the clean MP3 file
                            new_path, error = tts_module.change_voice_from_audio(char, temp_mp3_path)
                        
                        if error:
                            st.error(f"Voice changing failed: {error}")
                        else:
                            st.session_state.generated_audio_paths[line_index] = new_path
                            st.session_state.recording_for_line = None
                            st.success("Audio updated from recording!")
                            st.rerun()

                if st.button("Cancel Recording", key=f"cancel_rec_{line_index}"):
                    st.session_state.recording_for_line = None
                    st.rerun()

with tabs[1]:
    st.subheader("📽️ Assemble Final Cartoon")
        # --- New UI for Background Audio ---
    st.session_state.background_audio = st.file_uploader(
        "Upload a background audio track (optional)", type=['mp3', 'wav', 'm4a']
    )

    if not st.session_state.generated_audio_paths:
        st.info("Generate audio in Step 1 before creating the video.")
    else:
        if st.button("Generate Cartoon Video", use_container_width=True, type="primary"):
            with st.spinner("Assembling cartoon... This can take a minute!"):
                video_path, error = video_module.create_video_from_script(st.session_state.current_script, st.session_state.generated_audio_paths)
                if error: st.error(f"Video Failed: {error}")
                else: st.session_state.final_cartoon_path = video_path

    if st.session_state.final_cartoon_path:
        st.success("Cartoon generated successfully!")
        st.video(st.session_state.final_cartoon_path)

# --- Final Comic Files and Posting ---
st.divider()
st.header("🚀 Final Comic Files & Social Posting")
if st.session_state.generated_comic_paths:
    if not is_admin:
        st.info("Enter the correct password in the sidebar to enable uploading and posting.")
    else:
        st.subheader("1. Upload Comic to Imgur")
        if st.session_state.imgur_image_links:
            st.success("All images uploaded to Imgur!")
            with st.expander("View Imgur Links"):
                for i, link in enumerate(st.session_state.imgur_image_links):
                    st.markdown(f"- **Image {i+1}:** [{link}]({link})")
        else:
            if st.button("⬆️ Upload All 5 to Imgur", key="upload_all_imgur"):
                with st.spinner(f"Uploading {len(st.session_state.generated_comic_paths)} images to Imgur..."):
                    paths_to_upload = st.session_state.generated_comic_paths
                    public_urls, error_msg = imgur_uploader.upload_multiple_images_to_imgur(paths_to_upload)
                if public_urls:
                    st.session_state.imgur_image_links = public_urls; st.rerun()
                else:
                    st.error(f"Imgur Upload Failed: {error_msg}")
        
        st.subheader("2. Post Comic to Socials")
        st.markdown("##### Tailor Your Post Content:")
        cap_col1, cap_col2 = st.columns(2)
        with cap_col1:
            st.session_state.instagram_caption = st.text_area("🇮📷 Instagram Caption:", height=150, value=st.session_state.get('instagram_caption', ''))
            st.session_state.bluesky_caption = st.text_area("☁️ Bluesky Caption:", height=150, value=st.session_state.get('bluesky_caption', ''))
        with cap_col2:
            st.session_state.twitter_caption = st.text_area("🐦 Twitter Caption:", height=150, value=st.session_state.get('twitter_caption', ''))
            st.session_state.reddit_title = st.text_input("🤖 Reddit Title:", value=st.session_state.get('reddit_title', ''))
            st.session_state.reddit_subreddit = st.text_input("Subreddit (no r/):", value=st.session_state.get('reddit_subreddit', ''))
        
        st.markdown("##### Click to Post:")
        post_cols = st.columns(4)
        composite_image_path = st.session_state.generated_comic_paths[-1]

        with post_cols[0]: pass
        with post_cols[1]: pass
        with post_cols[2]: pass
        with post_cols[3]: pass
else:
    st.info("Finalize a comic preview to enable social media posting options.")
