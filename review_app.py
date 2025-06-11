# review_app.py
import streamlit as st
import comic_generator_module
import ai_script_module
import social_media_module
import imgur_uploader
import os

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
    st.session_state.current_script = """A: Another Tuesday.
B: Lucky us.
A: The data is particularly... beige today.
B: Don't get excited."""

if 'preview_image' not in st.session_state:
    st.session_state.preview_image = None

if 'generated_comic_paths' not in st.session_state:
    st.session_state.generated_comic_paths = []
if 'imgur_image_links' not in st.session_state:
    st.session_state.imgur_image_links = []

default_caption = "This comic is property of Gigo Co. #webcomic #gigo"
if 'instagram_caption' not in st.session_state: st.session_state.instagram_caption = default_caption
if 'bluesky_caption' not in st.session_state: st.session_state.bluesky_caption = default_caption
if 'twitter_caption' not in st.session_state: st.session_state.twitter_caption = default_caption

# --- Sidebar (Password Check) ---
st.sidebar.header("🔑 Admin Access")
is_admin = check_password()

# --- Main Area ---
st.header("📝 Script Editor")
st.write("Write your 4-line comic script below, or generate a new one with AI.")

st.session_state.current_script = st.text_area(
    "Comic Script",
    value=st.session_state.current_script,
    height=150,
    label_visibility="collapsed"
)

# --- Action Buttons ---
ai_col, preview_col, final_col = st.columns(3)

with ai_col:
    if st.button("🤖 Generate AI Script", use_container_width=True):
        with st.spinner("AI is drafting a new script..."):
            try:
                new_script = ai_script_module.generate_ai_script(num_script_options=1)
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

if st.session_state.preview_image:
    st.divider()
    st.header("👀 Preview")
    st.image(st.session_state.preview_image, use_container_width=True)

    with final_col:
        if st.button("✅ Approve & Generate Final Files", use_container_width=True):
            with st.spinner("Finalizing comic images..."):
                try:
                    generated_paths = comic_generator_module.generate_comic_from_script_text(st.session_state.current_script)
                    if generated_paths:
                        st.session_state.generated_comic_paths = generated_paths
                        st.session_state.imgur_image_links = []
                        st.success("Final comic files generated successfully!")
                        st.rerun()
                    else:
                        st.error("Image generation failed. Check the logs for details.")
                except Exception as e:
                    st.error("An unexpected error occurred during final image generation.")
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
        st.markdown("##### Tailor Your Captions:")
        caption_cols = st.columns(3)
        with caption_cols[0]:
            st.session_state.instagram_caption = st.text_area("🇮📷 Instagram:", value=st.session_state.instagram_caption, height=150)
        with caption_cols[1]:
            st.session_state.bluesky_caption = st.text_area("☁️ Bluesky:", value=st.session_state.bluesky_caption, height=150)
        with caption_cols[2]:
            st.session_state.twitter_caption = st.text_area("🐦 Twitter:", value=st.session_state.twitter_caption, height=150)

        st.markdown("##### Individual Platform Posting:")
        col_ig_post, col_bsky_post, col_twitter_post = st.columns(3)
        with col_ig_post:
            if st.button("🇮📷 Post Carousel to Instagram", key="post_ig_carousel_button_v2", use_container_width=True):
                if not st.session_state.imgur_image_links:
                    st.warning("Please upload all images to Imgur first.")
                elif not st.session_state.instagram_caption.strip():
                    st.warning("Please enter a caption for Instagram.")
                else:
                    with st.spinner("Posting carousel to Instagram..."):
                        post_success, message = social_media_module.post_carousel_to_instagram_graph_api(
                            st.session_state.imgur_image_links, st.session_state.instagram_caption
                        )
                    if post_success: st.success(f"Instagram: Posted! {message}")
                    else: st.error(f"Instagram: Failed! {message}")
        with col_bsky_post:
            if st.button("☁️ Post Composite to Bluesky", key="post_bsky_composite", use_container_width=True):
                if not st.session_state.bluesky_caption.strip(): st.warning("Bluesky caption needed.")
                else:
                    composite_image_path = st.session_state.generated_comic_paths[-1]
                    with st.spinner("Posting composite to Bluesky..."):
                        bsky_success, bsky_message = social_media_module.post_comic_to_bluesky(
                            composite_image_path, st.session_state.bluesky_caption
                        )
                    if bsky_success: st.success(f"Bluesky: Posted! {bsky_message}")
                    else: st.error(f"Bluesky: Failed! {bsky_message}")
        with col_twitter_post:
            if st.button("🐦 Post Composite to Twitter", key="post_twitter_composite", use_container_width=True):
                if not st.session_state.twitter_caption.strip(): st.warning("Twitter caption needed.")
                else:
                    composite_image_path = st.session_state.generated_comic_paths[-1]
                    with st.spinner("Posting composite to Twitter..."):
                        twitter_success, twitter_message = social_media_module.post_comic_to_twitter(
                            composite_image_path, st.session_state.twitter_caption
                        )
                    if twitter_success: st.success(f"Twitter: Posted! {twitter_message}")
                    else: st.error(f"Twitter: Failed! {twitter_message}")
    else:
        st.info("Enter the correct password in the sidebar to enable uploading and posting.")

