# review_app.py
import streamlit as st
import comic_generator_module
# ... other imports ...
import os

# ... (Helper function and initialization remains the same) ...
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

if 'preview_image' not in st.session_state:
    st.session_state.preview_image = None

if 'generated_comic_paths' not in st.session_state:
    st.session_state.generated_comic_paths = []

# ... (other session state inits) ...


# --- Sidebar ---
st.sidebar.header("🔑 Admin Access")
is_admin = check_password()
st.sidebar.divider()
# ... (rest of sidebar) ...


# --- Main Area ---
st.header("📝 Script Editor")
st.write("Write your 4-line comic script below. Use actions like (shocked) to change expressions.")

st.session_state.current_script = st.text_area(
    "Comic Script",
    value=st.session_state.current_script,
    height=150,
    placeholder="Example:\nA: What a day.\nB:(shocked) You can say that again!",
    label_visibility="collapsed"
)

# --- Action Buttons ---
# ... (AI Button remains the same) ...
ai_col, preview_col, final_col = st.columns(3)

with preview_col:
    if st.button("🖼️ Generate Preview", use_container_width=True):
        with st.spinner("Generating preview..."):
            try:
                # UPDATED to handle new return signature
                preview, error = comic_generator_module.generate_preview_image(st.session_state.current_script)
                
                if error:
                    st.error(f"Preview Failed: {error}")
                    st.session_state.preview_image = None
                else:
                    st.session_state.preview_image = preview
                
                # Clear any old final files when a new preview is made
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
                    # UPDATED to handle new return signature
                    final_paths, error = comic_generator_module.generate_comic_from_script_text(st.session_state.current_script)
                    
                    if error:
                        st.error(f"Finalization Failed: {error}")
                        st.session_state.generated_comic_paths = []
                    else:
                        st.session_state.generated_comic_paths = final_paths
                        st.session_state.imgur_image_links = []
                        st.success("Final comic files generated successfully!")
                        st.rerun()

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
