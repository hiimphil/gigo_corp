# review_app.py (with password protection)
import streamlit as st
import comic_generator_module
import ai_script_module
import social_media_module
import imgur_uploader
import os

# --- Helper Function for Password Check ---
def check_password():
    """Returns `True` if the user has the correct password."""

    # Use a sidebar input for the password.
    password = st.sidebar.text_input("Enter Password for Admin Access", type="password")

    # Check if the password is correct.
    if password == st.secrets.get("APP_PASSWORD"):
        return True
    elif password: # If a password was entered but is incorrect
        st.sidebar.warning("Incorrect password.")
        return False
    else: # If no password was entered
        return False

st.set_page_config(layout="wide")
st.title("Gigo Co. Comic Review & Approval ✨")

# --- Session State Initialization (No changes here) ---
if 'optional_theme' not in st.session_state:
    st.session_state.optional_theme = "a new mandatory 'synergy' workshop"
if 'num_script_options' not in st.session_state:
    st.session_state.num_script_options = 3
if 'generated_script_options' not in st.session_state:
    st.session_state.generated_script_options = []
if 'selected_script_option_index' not in st.session_state:
    st.session_state.selected_script_option_index = 0
if 'current_script' not in st.session_state:
    st.session_state.current_script = """A: Welcome, C, to the Input Department!
C: Thank you, Unit A! I'm thrilled for this synergy!
B: Another one.
A: Isn't Gigo Co. grand?"""
if 'generated_comic_paths' not in st.session_state:
    st.session_state.generated_comic_paths = []
if 'imgur_image_links' not in st.session_state:
    st.session_state.imgur_image_links = []
default_caption = "This comic is property of Gigo Co. Global leader in the data-backed human experience. #webcomic #gigo"
if 'instagram_caption' not in st.session_state: st.session_state.instagram_caption = default_caption
if 'bluesky_caption' not in st.session_state: st.session_state.bluesky_caption = default_caption
if 'twitter_caption' not in st.session_state: st.session_state.twitter_caption = default_caption


# --- Sidebar ---
st.sidebar.header("🤖 AI Script Generation")
st.session_state.optional_theme = st.sidebar.text_input(
    "Comic Theme (Optional):", value=st.session_state.optional_theme
)
st.session_state.num_script_options = st.sidebar.number_input(
    "Number of Script Options to Generate:", min_value=1, max_value=5,
    value=st.session_state.num_script_options, step=1
)
if st.sidebar.button("✨ Generate AI Scripts"):
    with st.spinner(f"AI is drafting {st.session_state.num_script_options} script(s)..."):
        scripts_or_error = ai_script_module.generate_ai_script(
            optional_theme=st.session_state.optional_theme,
            num_script_options=st.session_state.num_script_options
        )
    if isinstance(scripts_or_error, list) and scripts_or_error:
        st.session_state.generated_script_options = scripts_or_error
        st.session_state.selected_script_option_index = 0
        st.session_state.current_script = scripts_or_error[0]
        st.success(f"{len(scripts_or_error)} script options generated!")
    elif isinstance(scripts_or_error, str) and not scripts_or_error.startswith("Error:"):
        st.session_state.generated_script_options = [scripts_or_error]
        st.session_state.selected_script_option_index = 0
        st.session_state.current_script = scripts_or_error
        st.success("AI script generated!")
    else:
        st.error(f"Failed to generate scripts: {scripts_or_error}")

# --- NEW: Add a divider and the password check to the sidebar ---
st.sidebar.divider()
st.sidebar.header("🔑 Admin Access")
is_admin = check_password()


# --- Main Area ---
# Script selection and editing are always visible to everyone
if len(st.session_state.generated_script_options) > 0:
    st.header("📜 Choose Your Favorite Script Option")
    chosen_script_text = st.selectbox(
        "Select a script to edit:",
        options=st.session_state.generated_script_options,
        index=st.session_state.selected_script_option_index,
        format_func=lambda x: f"Option {st.session_state.generated_script_options.index(x) + 1}: {x.split(chr(10))[0]}..." if x and isinstance(x, str) else "Invalid Option"
    )
    if chosen_script_text and chosen_script_text != st.session_state.current_script:
        st.session_state.current_script = chosen_script_text
        st.session_state.selected_script_option_index = st.session_state.generated_script_options.index(chosen_script_text)
    st.markdown("---")
st.header("📝 Comic Script Editor")
st.session_state.current_script = st.text_area(
    "Edit the selected script here:",
    value=st.session_state.current_script,
    height=150
)
# In review_app.py

# --- Generate Comic Image Button ---
if st.button("🖼️ Generate Carousel Comic Images", key="generate_carousel_button"):
    if not st.session_state.current_script or len(st.session_state.current_script.split('\n')) != 4:
        st.warning("Please select or edit a valid 4-line script.")
    else:
        try: # --- ADD THIS TRY BLOCK ---
            with st.spinner("Generating 5 comic images for carousel..."):
                local_paths = comic_generator_module.generate_comic_from_script_text(st.session_state.current_script)
            
            if local_paths and all(os.path.exists(p) for p in local_paths):
                st.session_state.generated_comic_paths = local_paths
                st.session_state.imgur_image_links = [] 
                st.success("Carousel images generated successfully!")
            else:
                st.session_state.generated_comic_paths = []
                st.error("Failed to generate carousel images. Check console for details. It's possible the temporary files were not found.")

        except Exception as e: # --- ADD THIS EXCEPT BLOCK ---
            st.error("An unexpected error occurred during image generation!")
            st.exception(e) # This will print the full traceback to the screen
st.markdown("---")


# --- GATED CONTENT: This entire section is now wrapped in the 'if is_admin:' block ---
if st.session_state.generated_comic_paths and all(os.path.exists(p) for p in st.session_state.generated_comic_paths):
    st.header("👀 Carousel Preview")
    st.image(st.session_state.generated_comic_paths, width=200, caption=[f"Panel {i+1}" for i in range(4)] + ["Composite"])

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
                    st.session_state.generated_comic_paths,
                    title_prefix=f"GigoCo - {st.session_state.optional_theme}"
                )
            if public_urls:
                st.session_state.imgur_image_links = public_urls
                st.rerun()
            else:
                st.error(f"Imgur Upload Failed: {error_msg}")

        st.markdown("---")
        st.subheader("🚀 Approval & Posting")

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
                if not st.session_state.imgur_image_links or len(st.session_state.imgur_image_links) != 5:
                    st.warning("Please upload all 5 images to Imgur first.")
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
