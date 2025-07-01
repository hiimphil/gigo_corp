# ui_comic_maker.py
import streamlit as st
import time
import comic_generator_module
import ai_script_module
import database_module
import imgur_uploader
import instagram_module
import bluesky_module
import social_media_module
import reddit_module

def _init_social_keys():
    """
    A safeguard function to ensure all social media keys exist in the session state.
    This prevents AttributeErrors if the main app's initialization is missed on a rerun.
    """
    default_caption = "This comic is property of Gigo Co. #webcomic #gigo"
    if 'instagram_caption' not in st.session_state: st.session_state.instagram_caption = default_caption
    if 'bluesky_caption' not in st.session_state: st.session_state.bluesky_caption = default_caption
    if 'twitter_caption' not in st.session_state: st.session_state.twitter_caption = default_caption
    if 'reddit_title' not in st.session_state: st.session_state.reddit_title = "Gigo Corp Comic"
    if 'reddit_subreddit' not in st.session_state: st.session_state.reddit_subreddit = "GigoCorp"

def reset_comic_state():
    """Resets the state specific to the comic maker."""
    st.session_state.preview_image = None
    st.session_state.generated_comic_paths = []
    st.session_state.imgur_image_links = []

def display(is_admin):
    """Renders the entire UI for the Web Comic Maker workflow."""
    st.header("Web Comic Maker")
    st.write("Create a classic 4-panel Gigo Corp comic strip and post it to your social media accounts.")
    st.divider()

    # --- Script Library for Comics ---
    st.subheader("📜 Comic Script Library")
    comic_scripts = database_module.load_scripts("comic_scripts")
    if comic_scripts:
        script_to_load = st.selectbox(
            "Select a comic script:", 
            options=list(comic_scripts.keys()), 
            index=None, 
            placeholder="-- Choose a script to load --",
            key="comic_script_selectbox"
        )
        load_col, delete_col = st.columns(2)
        with load_col:
            if st.button("Load Comic Script", use_container_width=True):
                if script_to_load:
                    st.session_state.comic_script = comic_scripts[script_to_load]
                    st.session_state.comic_title = script_to_load
                    st.rerun()
        with delete_col:
            if st.button("Delete Comic Script", use_container_width=True):
                if script_to_load and is_admin:
                    database_module.delete_script(script_to_load, "comic_scripts")
                    st.toast(f"Deleted '{script_to_load}'")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("No comic scripts saved yet.")
    st.divider()

    # --- Comic Script Editor ---
    st.subheader("📝 Comic Script Editor")
    st.session_state.comic_title = st.text_input("Comic Title:", value=st.session_state.get('comic_title', ''))
    st.session_state.comic_script = st.text_area(
        "Comic Script (4 lines)", 
        value=st.session_state.get('comic_script', ''), 
        height=150,
        key="comic_script_editor"
    )

    # --- Action Buttons for Comic Script ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💾 Save Comic Script", use_container_width=True):
            if is_admin:
                database_module.save_script(st.session_state.comic_title, st.session_state.comic_script, "comic_scripts")
                st.toast("Comic script saved!")
            else:
                st.warning("Admin access required.")
    with col2:
        if st.button("🤖 Generate or Complete Script", use_container_width=True):
            with st.spinner("AI is drafting a script..."):
                new_script = ai_script_module.generate_comic_script(partial_script=st.session_state.comic_script)
                if new_script and not new_script.startswith("Error:"):
                    st.session_state.comic_script = new_script
                    reset_comic_state()
                    st.rerun()
                else:
                    st.error(f"AI Failed: {new_script}")
    with col3:
        if st.button("🖼️ Generate Preview", use_container_width=True):
            reset_comic_state()
            with st.spinner("Generating preview..."):
                preview, error = comic_generator_module.generate_preview_image(st.session_state.comic_script)
                if error:
                    st.error(f"Preview Failed: {error}")
                else:
                    st.session_state.preview_image = preview
                    st.rerun()

    # --- Comic Preview and Finalize Button ---
    if st.session_state.get('preview_image'):
        st.divider()
        st.header("👀 Comic Preview")
        st.image(st.session_state.preview_image, use_container_width=True)
        with col4:
            if st.button("✅ Approve & Finalize Comic", use_container_width=True, type="primary"):
                with st.spinner("Finalizing comic images..."):
                    final_paths, error = comic_generator_module.generate_comic_from_script_text(st.session_state.comic_script)
                    if error:
                        st.error(f"Finalization Failed: {error}")
                    else:
                        st.session_state.generated_comic_paths = final_paths
                        st.success("Final comic files generated!")
                        st.rerun()
    
    # --- Social Media Posting Section ---
    display_social_poster(is_admin)

def display_social_poster(is_admin):
    """Renders the UI for uploading and posting the static comic."""
    st.divider()
    st.header("🚀 Final Comic Files & Social Posting")
    
    if not st.session_state.get('generated_comic_paths'):
        st.info("Finalize a comic preview to enable social media posting options.")
        return

    if not is_admin:
        st.info("Enter the correct password in the sidebar to enable uploading and posting.")
        return
    
    # Call the safeguard function to ensure keys exist
    _init_social_keys()
        
    # --- Imgur Uploading ---
    st.subheader("1. Upload Comic to Imgur")
    if st.session_state.get('imgur_image_links'):
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
                st.session_state.imgur_image_links = public_urls
                st.rerun()
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

    with post_cols[0]: # INSTAGRAM
        if st.button("🇮📷 Post to Instagram", use_container_width=True):
            if not st.session_state.get('imgur_image_links'):
                st.warning("Please upload to Imgur first.")
            else:
                ig_urls = st.session_state.imgur_image_links[:4] + [st.session_state.imgur_image_links[-1]]
                with st.spinner("Posting to Instagram... this can take a moment."):
                    success, message = instagram_module.post_carousel_to_instagram_graph_api(ig_urls, st.session_state.instagram_caption)
                    if success: st.success(f"Posted to Instagram! {message}")
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
                success, message = reddit_module.post_comic_to_reddit(composite_image_path, st.session_state.reddit_title, st.session_state.reddit_subreddit)
                if success: st.success(f"Posted to Reddit! {message}")
                else: st.error(f"Reddit Failed: {message}")
