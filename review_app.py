# review_app.py
import streamlit as st
import comic_generator_module
import ai_script_module
import social_media_module 
import bluesky_module
import instagram_module
import imgur_uploader
import database_module
import reddit_module
import tts_module # <-- New import for Text-to-Speech
import os
import time

# --- Database Initialization (Handled in module) ---

# --- Helper Function for Password Check ---
def check_password():
    """Returns `True` if the user has the correct password."""
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

# --- Session State Initialization ---
if 'current_script' not in st.session_state: st.session_state.current_script = ""
if 'script_title' not in st.session_state: st.session_state.script_title = "My First Comic"
if 'preview_image' not in st.session_state: st.session_state.preview_image = None
if 'generated_comic_paths' not in st.session_state: st.session_state.generated_comic_paths = []
if 'imgur_image_links' not in st.session_state: st.session_state.imgur_image_links = []
if 'generated_audio_paths' not in st.session_state: st.session_state.generated_audio_paths = {} # <-- New state for audio

# --- Social Media State ---
default_caption = "This comic is property of Gigo Co. #webcomic #gigo"
if 'instagram_caption' not in st.session_state: st.session_state.instagram_caption = default_caption
if 'bluesky_caption' not in st.session_state: st.session_state.bluesky_caption = default_caption
if 'twitter_caption' not in st.session_state: st.session_state.twitter_caption = default_caption
if 'reddit_title' not in st.session_state: st.session_state.reddit_title = "Gigo Corp Comic"
if 'reddit_subreddit' not in st.session_state: st.session_state.reddit_subreddit = "GigoCorp"

# --- Sidebar ---
st.sidebar.header("🔑 Admin Access")
is_admin = check_password()
st.sidebar.divider()
# ... (rest of the sidebar is unchanged) ...
st.sidebar.header("🎨 Action Guide")
st.sidebar.write("Use `(action)` or `(direction)` in a script line.")
st.sidebar.code("A:(left) Hi!\nB:(shocked) Hello.")
available_actions = comic_generator_module.get_available_actions()
if available_actions:
    for char, states in available_actions.items():
        with st.sidebar.expander(f"Character {char} Actions"):
            for state, directions in states.items():
                st.write(f"**{state}:**")
                for direction, actions in directions.items():
                    if actions:
                        st.write(f"- _{direction}_: {', '.join(actions)}")
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


# --- Main Area ---
st.header("📝 Script Editor")
st.session_state.script_title = st.text_input("Script Title:", st.session_state.script_title)
st.session_state.current_script = st.text_area("Comic Script", value=st.session_state.current_script, height=150, placeholder="A: I filed the report.\nB:(proud) You filed the report.\nA: It was a good report.\nB:(left) Indeed.", label_visibility="collapsed")

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
                st.session_state.preview_image = None; st.session_state.generated_comic_paths = []; st.session_state.generated_audio_paths = {}
                st.rerun()
            else: st.error(f"AI Failed: {new_script}")

with col3:
    if st.button("🖼️ Generate Preview", use_container_width=True):
        st.session_state.generated_comic_paths = []; st.session_state.generated_audio_paths = {}
        with st.spinner("Generating preview..."):
            preview, error = comic_generator_module.generate_preview_image(st.session_state.current_script)
            if error: st.error(f"Preview Failed: {error}"); st.session_state.preview_image = None
            else: st.session_state.preview_image = preview

if st.session_state.preview_image:
    st.divider()
    st.header("👀 Preview")
    st.image(st.session_state.preview_image, use_container_width=True)
    with col4:
        if st.button("✅ Approve & Finalize", use_container_width=True, type="primary"):
            st.session_state.generated_audio_paths = {} # Clear old audio
            with st.spinner("Finalizing comic images..."):
                final_paths, error = comic_generator_module.generate_comic_from_script_text(st.session_state.current_script)
                if error: st.error(f"Finalization Failed: {error}"); st.session_state.generated_comic_paths = []
                else: st.session_state.generated_comic_paths = final_paths; st.session_state.imgur_image_links = []; st.success("Final comic files generated!"); st.rerun()
    st.divider()

# --- NEW SECTION: Audio Generation ---
if st.session_state.generated_comic_paths and is_admin:
    st.header("🔊 Audio Generation")

    # Display the audio generation button
    if st.button("🎤 Generate Audio for Script", use_container_width=True):
        audio_paths = {}
        lines = st.session_state.current_script.strip().split('\n')
        with st.spinner("Generating audio for each line..."):
            for i, line in enumerate(lines):
                # We need to parse the line to get the character and dialogue
                char, _, _, dialogue = comic_generator_module.parse_script_line(line)
                if char and dialogue:
                    path, error = tts_module.generate_speech_for_line(char, dialogue)
                    if error:
                        st.error(f"Audio failed for line {i+1}: {error}")
                        audio_paths = {} # Clear results on failure
                        break
                    audio_paths[i] = path # Store path with line index
                else:
                    audio_paths[i] = None # Represents a pause
            
            st.session_state.generated_audio_paths = audio_paths
            if audio_paths:
                st.success("Audio generated for all lines!")

    # Display the generated audio files
    if st.session_state.generated_audio_paths:
        st.subheader("Playback Script Audio")
        lines = st.session_state.current_script.strip().split('\n')
        for i, line in enumerate(lines):
            st.write(f"**Line {i+1}:** *{line.strip()}*")
            audio_path = st.session_state.generated_audio_paths.get(i)
            if audio_path:
                st.audio(audio_path)
            else:
                st.info("_(This line has no dialogue.)_")
        st.divider()

if st.session_state.generated_comic_paths:
    st.header("🚀 Final Files & Posting")
    
    # Select which image to use for single-image posts
    composite_image_path = st.session_state.generated_comic_paths[-1]
    
    with st.expander("View Final Images (5 total)"):
        st.image(composite_image_path, caption="Composite Image")
        img_cols = st.columns(4)
        for i in range(4):
            with img_cols[i]:
                st.image(st.session_state.generated_comic_paths[i], caption=f"Panel {i+1}")

    if not is_admin:
        st.info("Enter the correct password in the sidebar to enable uploading and posting.")
    else:
        # --- IMGUR UPLOADING ---
        st.subheader("1. Upload to Imgur (for Instagram)")
        if st.session_state.imgur_image_links:
            st.success("All images uploaded to Imgur!")
        else:
            if st.button("⬆️ Upload All 5 to Imgur", key="upload_all_imgur"):
                with st.spinner(f"Uploading {len(st.session_state.generated_comic_paths)} images to Imgur..."):
                    # We need the 4 individual panels + the composite for a 5-image carousel
                    paths_to_upload = st.session_state.generated_comic_paths
                    public_urls, error_msg = imgur_uploader.upload_multiple_images_to_imgur(paths_to_upload)
                if public_urls:
                    st.session_state.imgur_image_links = public_urls
                    st.rerun()
                else:
                    st.error(f"Imgur Upload Failed: {error_msg}")

        # --- SOCIAL MEDIA POSTING ---
        st.subheader("2. Post to Socials")
        st.markdown("##### Tailor Your Post Content:")
        cap_col1, cap_col2 = st.columns(2)
        with cap_col1:
            st.session_state.instagram_caption = st.text_area("🇮📷 Instagram Caption:", height=150, value=st.session_state.instagram_caption)
            st.session_state.bluesky_caption = st.text_area("☁️ Bluesky Caption:", height=150, value=st.session_state.bluesky_caption)
        with cap_col2:
            st.session_state.twitter_caption = st.text_area("🐦 Twitter Caption:", height=150, value=st.session_state.twitter_caption)
            st.session_state.reddit_title = st.text_input("🤖 Reddit Title:", value=st.session_state.reddit_title)
            st.session_state.reddit_subreddit = st.text_input("Subreddit (no r/):", value=st.session_state.reddit_subreddit)

        st.markdown("##### Click to Post:")
        post_cols = st.columns(4)
        
        with post_cols[0]: # INSTAGRAM
            if st.button("🇮📷 Post to Instagram", use_container_width=True):
                if not st.session_state.imgur_image_links:
                    st.warning("Please upload to Imgur first.")
                else:
                    # Instagram allows up to 10 images. We have 5 (4 panels + 1 composite).
                    # Let's send the 4 panels first, then the composite.
                    ig_urls = st.session_state.imgur_image_links[:4] + [st.session_state.imgur_image_links[-1]]
                    with st.spinner("Posting to Instagram... this can take a moment."):
                        success, message = instagram_module.post_carousel_to_instagram_graph_api(ig_urls, st.session_state.instagram_caption)
                        if success: st.success(f"Posted to Instagram! {message}"); 
                        else: st.error(f"Instagram Failed: {message}")

        with post_cols[1]: # BLUESKY
            if st.button("☁️ Post to Bluesky", use_container_width=True):
                with st.spinner("Posting to Bluesky..."):
                    success, message = bluesky_module.post_comic_to_bluesky(composite_image_path, st.session_state.bluesky_caption)
                    if success: st.success(f"Posted to Bluesky! {message}")
                    else: st.error(f"Bluesky Failed: {message}")
        
        with post_cols[2]: # TWITTER
            if st.button("🐦 Post to Twitter", use_container_width=True):
                with st.spinner("Posting to Twitter..."):
                    success, message = social_media_module.post_comic_to_twitter(composite_image_path, st.session_state.twitter_caption)
                    if success: st.success(f"Posted to Twitter! {message}")
                    else: st.error(f"Twitter Failed: {message}")
        
        with post_cols[3]: # REDDIT
            if st.button("🤖 Post to Reddit", use_container_width=True):
                with st.spinner("Posting to Reddit..."):
                    # Use the new, separate module
                    success, message = reddit_module.post_comic_to_reddit(composite_image_path, st.session_state.reddit_title, st.session_state.reddit_subreddit)
                    if success: st.success(f"Posted to Reddit! {message}")
                    else: st.error(f"Reddit Failed: {message}")
