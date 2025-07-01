# review_app.py
import os
import time
os.environ['MAGICK_CONFIGURE_PATH'] = '.'

import streamlit as st

# Import the new UI modules
import ui_sidebar
import ui_editor
import ui_cartoon_generator
import ui_social_poster

# --- Session State Initialization ---
# This block ensures all keys exist before any UI is rendered.
def init_session_state():
    if 'current_script' not in st.session_state: st.session_state.current_script = ""
    if 'script_title' not in st.session_state: st.session_state.script_title = "My First Comic"
    if 'preview_image' not in st.session_state: st.session_state.preview_image = None
    if 'generated_comic_paths' not in st.session_state: st.session_state.generated_comic_paths = []
    if 'imgur_image_links' not in st.session_state: st.session_state.imgur_image_links = []
    if 'generated_audio_paths' not in st.session_state: st.session_state.generated_audio_paths = {}
    if 'final_cartoon_path' not in st.session_state: st.session_state.final_cartoon_path = None
    if 'background_audio' not in st.session_state: st.session_state.background_audio = None
    
    default_caption = "This comic is property of Gigo Co. #webcomic #gigo"
    if 'instagram_caption' not in st.session_state: st.session_state.instagram_caption = default_caption
    if 'bluesky_caption' not in st.session_state: st.session_state.bluesky_caption = default_caption
    if 'twitter_caption' not in st.session_state: st.session_state.twitter_caption = default_caption
    if 'reddit_title' not in st.session_state: st.session_state.reddit_title = "Gigo Corp Comic"
    if 'reddit_subreddit' not in st.session_state: st.session_state.reddit_subreddit = "GigoCorp"

# --- Main App Logic ---
def main():
    """Main function to run the Streamlit app."""
    # Initialize session state at the very beginning
    init_session_state()

    st.set_page_config(layout="wide")
    st.title("Gigo Corp Comic & Cartoon Builder")

    # Display the sidebar and get the admin status
    is_admin = ui_sidebar.display_sidebar()

    # Display the main UI sections by calling functions from the new modules
    ui_editor.display_editor(is_admin)
    ui_cartoon_generator.display_cartoon_generator()
    ui_social_poster.display_social_poster(is_admin)

if __name__ == "__main__":
    main()
