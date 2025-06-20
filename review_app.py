# review_app.py
import streamlit as st
import comic_generator_module
import ai_script_module
import social_media_module 
import bluesky_module
import instagram_module
import imgur_uploader
import database_module # Import our new database module
import os
import praw

# --- Initialize the database ---
database_module.init_db()

# --- Helper Function for Password Check ---
def check_password():
    """Returns `True` if the user has the correct password."""
    try:
        password = st.sidebar.text_input("Enter Password for Admin Access", type="password")
        if password == st.secrets.get("APP_PASSWORD"):
            return True
        elif password:
            st.sidebar.warning("Incorrect password.")
            return False
        else:
            return False
    except Exception:
        # This handles the case where secrets are not set up locally
        st.sidebar.info("Password feature is disabled for local development.")
        return True

st.set_page_config(layout="wide")
st.title("Gigo Corp Comic Builder")

# --- Session State Initialization ---
if 'current_script' not in st.session_state:
    st.session_state.current_script = ""
if 'script_title' not in st.session_state:
    st.session_state.script_title = "My First Comic"
if 'preview_image' not in st.session_state:
    st.session_state.preview_image = None
if 'generated_comic_paths' not in st.session_state:
    st.session_state.generated_comic_paths = []
if 'imgur_image_links' not in st.session_state:
    st.session_state.imgur_image_links = []

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

# --- NEW: Script Library in Sidebar ---
st.sidebar.header("📜 Script Library")
saved_scripts = database_module.load_scripts()

# Load Script Dropdown
if saved_scripts:
    # Use a blank option to prevent auto-loading on first run
    script_options = ["-- Select a script to load --"] + list(saved_scripts.keys())
    selected_script_title = st.sidebar.selectbox(
        "Load a saved script:",
        options=script_options,
        key='load_script_selectbox'
    )
    if selected_script_title != "-- Select a script to load --":
        # Load the script and title into session state
        st.session_state.current_script = saved_scripts[selected_script_title]
        st.session_state.script_title = selected_script_title
        # Reset the selectbox to avoid reloading on every rerun
        st.session_state.load_script_selectbox = "-- Select a script to load --"
        st.rerun() # Rerun to update the text area immediately
else:
    st.sidebar.write("No saved scripts yet.")

st.sidebar.divider()


# --- Main Area ---
st.header("📝 Script Editor")
st.write("Write your 4-line comic script below, or let the AI complete your thought.")

# --- Text input for the script title ---
st.session_state.script_title = st.text_input("Script Title:", st.session_state.script_title)

st.session_state.current_script = st.text_area(
    "Comic Script",
    value=st.session_state.current_script,
    height=150,
    placeholder="Start writing your script here...",
    label_visibility="collapsed"
)

# --- Action Buttons ---
save_col, ai_col, preview_col, final_col = st.columns(4)

with save_col:
    if st.button("💾 Save Script", use_container_width=True):
        if is_admin:
            success, message = database_module.save_script(
                st.session_state.script_title,
                st.session_state.current_script
            )
            if success:
                st.success(message)
                # No rerun needed here, just a success message
            else:
                st.error(message)
        else:
            st.warning("You must be an admin to save scripts.")

with ai_col:
    if st.button("🤖 Generate or Complete Script", use_container_width=True):
        spinner_text = "AI is completing your script..." if st.session_state.current_script.strip() else "AI is drafting a new script..."
        with st.spinner(spinner_text):
            try:
                new_script = ai_script_module.generate_ai_script(partial_script=st.session_state.current_script)
                if new_script and not new_script.startswith("Error:"):
                    st.session_state.current_script = new_script
                    st.session_state.preview_image = None
                    st.session_state.generated_comic_paths = []
                    st.rerun()
                else:
                    st.error(f"Failed to generate AI script: {new_script}")
            except Exception as e:
                st.error("An unexpected error occurred during AI script generation.")
                st.exception(e)

with preview_col:
    if st.button("🖼️ Generate Preview", use_container_width=True):
        if not st.session_state.current_script or len(st.session_state.current_script.strip().split('\n')) != 4:
            st.warning("Please ensure your script has exactly 4 lines.")
        else:
            with st.spinner("Generating preview..."):
                try:
                    preview = comic_generator_module.generate_preview_image(st.session_state.current_script)
                    st.session_state.preview_image = preview
                    st.session_state.generated_comic_paths = []
                except Exception as e:
                    st.error("An unexpected error occurred during preview generation.")
                    st.exception(e)

# --- Display Preview Image ---
if st.session_state.preview_image:
    st.divider()
    st.header("👀 Preview")
    st.image(st.session_state.preview_image, use_container_width=True)

    with final_col:
        if st.button("✅ Approve & Finalize", use_container_width=True):
            with st.spinner("Finalizing comic images..."):
                try:
                    generated_paths = comic_generator_module.generate_comic_from_script_text(st.session_state.current_script)
                    if generated_paths:
                        st.session_state.generated_comic_paths = generated_paths
                        st.session_state.imgur_image_links = []
                        st.success("Final comic files generated successfully!")
                        st.rerun()
                    else:
                        st.error("Image generation failed.")
                except Exception as e:
                    st.error("An unexpected error occurred during final generation.")
                    st.exception(e)
    st.divider()

# --- GATED CONTENT: Final Files and Posting Section ---
if st.session_state.generated_comic_paths:
    st.header("🚀 Final Files & Posting")
    st.write("Your final, high-resolution files are ready for posting.")
    
    with st.expander("View Individual Panels"):
        preview_cols = st.columns(4)
        for i in range(4):
            with preview_cols[i]:
                st.image(st.session_state.generated_comic_paths[i])

    if is_admin:
        st.subheader("📤 Upload to Imgur")
        if st.session_state.imgur_image_links:
            st.success("All images uploaded to Imgur!")
            with st.expander("View Imgur Links"):
                for i, link in enumerate(st.session_state.imgur_image_links):
                    st.markdown(f"- **Image {i+1}:** [{link}]({link})")

        if st.button("⬆️ Upload All to Imgur", key="upload_all_imgur_button"):
            with st.spinner(f"Uploading {len(st.session_state.generated_comic_paths)} images to Imgur..."):
                public_urls, error_msg = imgur_uploader.upload_multiple_images_to_imgur(
                    st.session_state.generated_comic_paths
                )
            if public_urls:
                st.session_state.imgur_image_links = public_urls
                st.rerun()
            else:
                st.error(f"Imgur Upload Failed: {error_msg}")
        
        st.divider()
        st.subheader("🚀 Post to Socials")
        st.markdown("##### Tailor Your Post Content:")
        
        caption_cols = st.columns(4)
        with caption_cols[0]:
            st.session_state.instagram_caption = st.text_area("🇮📷 Instagram Caption:", value=st.session_state.instagram_caption, height=150)
        with caption_cols[1]:
            st.session_state.bluesky_caption = st.text_area("☁️ Bluesky Caption:", value=st.session_state.bluesky_caption, height=150)
        with caption_cols[2]:
            st.session_state.twitter_caption = st.text_area("🐦 Twitter Caption:", value=st.session_state.twitter_caption, height=150)
        with caption_cols[3]:
            st.session_state.reddit_title = st.text_input("🤖 Reddit Title:", value=st.session_state.reddit_title)
            st.session_state.reddit_subreddit = st.text_input("Subreddit:", value=st.session_state.reddit_subreddit)


        st.markdown("##### Individual Platform Posting:")
        post_cols = st.columns(4)
        
        with post_cols[0]:
            if st.button("🇮📷 Post Carousel to Instagram", key="post_ig_carousel_button_v2", use_container_width=True):
                # ...
                pass

        with post_cols[1]:
            if st.button("☁️ Post Composite to Bluesky", key="post_bsky_composite", use_container_width=True):
                # ...
                pass
        
        with post_cols[2]:
            if st.button("🐦 Post Composite to Twitter", key="post_twitter_composite", use_container_width=True):
                # ...
                pass
        
        with post_cols[3]:
            if st.button("🤖 Post Composite to Reddit", key="post_reddit_composite", use_container_width=True):
                # ...
                pass
    else:
        st.info("Enter the correct password in the sidebar to enable uploading and posting.")
