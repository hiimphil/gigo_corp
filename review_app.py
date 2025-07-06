# review_app.py
import os
os.environ['MAGICK_CONFIGURE_PATH'] = '.'

import streamlit as st

# Import the new, separated UI modules
import ui_sidebar
import ui_comic_maker
import ui_cartoon_maker
import ui_frame_extractor
import ui_video_tracker

# --- Session State Initialization ---
# This block ensures all keys exist before any UI is rendered.
def init_session_state():
    # Comic Maker State
    if 'comic_script' not in st.session_state: st.session_state.comic_script = ""
    if 'comic_title' not in st.session_state: st.session_state.comic_title = "My First Comic"
    if 'preview_image' not in st.session_state: st.session_state.preview_image = None
    if 'generated_comic_paths' not in st.session_state: st.session_state.generated_comic_paths = []
    if 'imgur_image_links' not in st.session_state: st.session_state.imgur_image_links = []
    
    # Cartoon Maker State
    if 'cartoon_script' not in st.session_state: st.session_state.cartoon_script = ""
    if 'cartoon_title' not in st.session_state: st.session_state.cartoon_title = "My First Cartoon"
    if 'generated_audio_paths' not in st.session_state: st.session_state.generated_audio_paths = {}
    if 'audio_generation_status' not in st.session_state: st.session_state.audio_generation_status = {}
    if 'final_cartoon_path' not in st.session_state: st.session_state.final_cartoon_path = None
    if 'background_audio' not in st.session_state: st.session_state.background_audio = None
    
    # Social Media State (shared for now, can be separated later)
    default_caption = "This comic is property of Gigo Co. #webcomic #gigo"
    if 'instagram_caption' not in st.session_state: st.session_state.instagram_caption = default_caption
    if 'bluesky_caption' not in st.session_state: st.session_state.bluesky_caption = default_caption
    if 'twitter_caption' not in st.session_state: st.session_state.twitter_caption = default_caption
    if 'reddit_title' not in st.session_state: st.session_state.reddit_title = "Gigo Corp Comic"
    if 'reddit_subreddit' not in st.session_state: st.session_state.reddit_subreddit = "GigoCorp"

# --- Main App Logic ---
def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(layout="wide")
    
    # Initialize session state at the very beginning
    init_session_state()

    st.title("Gigo Corp Content Builder")

    # The sidebar is now simpler and only returns the admin status
    is_admin = ui_sidebar.display_sidebar()

    # Create the main tabs for the different workflows
    comic_tab, cartoon_tab, extractor_tab, tracker_tab = st.tabs([
        "**Web Comic Maker**", 
        "**Cartoon Maker**", 
        "**Frame Extractor**", 
        "**Video Tracker**"
    ])

    with comic_tab:
        ui_comic_maker.display(is_admin)

    with cartoon_tab:
        ui_cartoon_maker.display(is_admin)
    
    with extractor_tab:
        ui_frame_extractor.display()
    
    with tracker_tab:
        ui_video_tracker.display()

if __name__ == "__main__":
    main()
