# review_app.py
import streamlit as st
import comic_generator_module
import ai_script_module
import social_media_module 
import bluesky_module
import instagram_module
import imgur_uploader
import database_module
import reddit_module # <-- New import
import os
import time

import streamlit as st
st.write(st.secrets.get("test_message", "Secrets file NOT loaded."))

# --- Initialize the database ---
database_module.init_db()

# --- Helper Function for Password Check ---
def check_password():
    """Returns `True` if the user has the correct password."""
    try:
        password = st.sidebar.text_input("Enter Password for Admin Access", type="password")
        # Use st.secrets for deployment
        if "APP_PASSWORD" in st.secrets and password == st.secrets.get("APP_PASSWORD"):
            return True
        # Fallback for local development if secrets aren't set
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
st.title("Gigo Corp Comic Builder")

# --- Session State Initialization ---
if 'current_script' not in st.session_state: st.session_state.current_script = ""
if 'script_title' not in st.session_state: st.session_state.script_title = "My First Comic"
if 'preview_image' not in st.session_state: st.session_state.preview_image = None
if 'generated_comic_paths' not in st.session_state: st.session_state.generated_comic_paths = []
if 'imgur_image_links' not in st.session_state: st.session_state.imgur_image_links = []

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
# Add this to review_app.py

st.sidebar.header("🔑 Admin Access")
is_admin = check_password()

# --- START OF DEBUGGING SNIPPET ---
if is_admin:
    with st.sidebar.expander("🕵️‍♀️ Secrets Inspector", expanded=True):
        try:
            creds = st.secrets["firebase_credentials"]
            st.success("Found 'firebase_credentials' section in secrets.")
            
            output = "Inspecting the dictionary structure:\n\n"
            
            required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
            
            for key in required_keys:
                if key not in creds:
                    output += f"❌ MISSING KEY: '{key}'\n"
                else:
                    value = creds[key]
                    val_type = type(value).__name__
                    
                    if key == "private_key":
                        # Don't display the full key for security
                        val_preview = f"'{value[:30]}...{value[-30:]}'"
                        output += f"✅ Key: '{key}', Type: {val_type}\n"
                    else:
                        output += f"✅ Key: '{key}', Type: {val_type}, Value: '{value}'\n"
            
            st.code(output, language="text")

        except Exception as e:
            st.error("Could not read or parse 'firebase_credentials' section.")
            st.exception(e)
# --- END OF DEBUGGING SNIPPET ---

st.sidebar.divider()
st.sidebar.divider()

# --- Action Guide ---
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

# --- Script Library ---
st.sidebar.header("📜 Script Library")
saved_scripts = database_module.load_scripts()
if saved_scripts:
    script_to_load = st.sidebar.selectbox("Select a script:", options=list(saved_scripts.keys()), index=None, placeholder="-- Choose a script to load --")
    if st.sidebar.button("Load Script"):
        if script_to_load:
            st.session_state.current_script = saved_scripts[script_to_load]
            st.session_state.script_title = script_to_load
            st.rerun()
else:
    st.sidebar.write("No saved scripts yet.")

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
            st.toast(message, icon="✅" if success else "❌")
        else:
            st.warning("You must be an admin to save scripts.")

with col2:
    if st.button("🤖 Generate or Complete Script", use_container_width=True):
        spinner_text = "AI is completing your script..." if st.session_state.current_script.strip() else "AI is drafting a new script..."
        with st.spinner(spinner_text):
            new_script = ai_script_module.generate_ai_script(partial_script=st.session_state.current_script)
            if new_script and not new_script.startswith("Error:"):
                st.session_state.current_script = new_script
                st.session_state.preview_image = None; st.session_state.generated_comic_paths = []
                st.rerun()
            else:
                st.error(f"AI Failed: {new_script}")

with col3:
    if st.button("🖼️ Generate Preview", use_container_width=True):
        with st.spinner("Generating preview..."):
            preview, error = comic_generator_module.generate_preview_image(st.session_state.current_script)
            if error:
                st.error(f"Preview Failed: {error}"); st.session_state.preview_image = None
            else:
                st.session_state.preview_image = preview
            st.session_state.generated_comic_paths = [] # Clear old final files on new preview

if st.session_state.preview_image:
    st.divider()
    st.header("👀 Preview")
    st.image(st.session_state.preview_image, use_container_width=True)
    with col4:
        if st.button("✅ Approve & Finalize", use_container_width=True, type="primary"):
            with st.spinner("Finalizing comic images..."):
                final_paths, error = comic_generator_module.generate_comic_from_script_text(st.session_state.current_script)
                if error:
                    st.error(f"Finalization Failed: {error}"); st.session_state.generated_comic_paths = []
                else:
                    st.session_state.generated_comic_paths = final_paths
                    st.session_state.imgur_image_links = [] # Clear old links
                    st.success("Final comic files generated successfully!")
                    st.rerun()
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
