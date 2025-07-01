# ui_social_poster.py
import streamlit as st
import imgur_uploader
import instagram_module
import bluesky_module
import social_media_module
import reddit_module

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
