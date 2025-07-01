# ui_editor.py
import streamlit as st
import time
import comic_generator_module
import ai_script_module
import database_module

def reset_downstream_state():
    """Resets all generated content when the script or preview changes."""
    st.session_state.preview_image = None
    st.session_state.generated_comic_paths = []
    st.session_state.generated_audio_paths = {}
    st.session_state.final_cartoon_path = None
    st.session_state.imgur_image_links = []

def display_editor(is_admin):
    """Renders the main script editor, action buttons, and comic preview."""
    st.header("📝 Script Editor")
    st.session_state.script_title = st.text_input("Script Title:", value=st.session_state.get('script_title', ''))
    st.session_state.current_script = st.text_area("Comic Script", value=st.session_state.get('current_script', ''), height=150)

    # --- Action Buttons ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💾 Save Script", use_container_width=True):
            if is_admin:
                success, message = database_module.save_script(st.session_state.script_title, st.session_state.current_script)
                st.toast(message, icon="✅" if success else "❌")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("You must be an admin to save scripts.")

    with col2:
        if st.button("🤖 Generate or Complete Script", use_container_width=True):
            with st.spinner("AI is working..."):
                new_script = ai_script_module.generate_ai_script(partial_script=st.session_state.current_script)
                if new_script and not new_script.startswith("Error:"):
                    st.session_state.current_script = new_script
                    reset_downstream_state()
                    st.rerun()
                else:
                    st.error(f"AI Failed: {new_script}")

    with col3:
        if st.button("🖼️ Generate Preview", use_container_width=True):
            reset_downstream_state()
            with st.spinner("Generating preview..."):
                preview, error = comic_generator_module.generate_preview_image(st.session_state.current_script)
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
                    final_paths, error = comic_generator_module.generate_comic_from_script_text(st.session_state.current_script)
                    if error:
                        st.error(f"Finalization Failed: {error}")
                    else:
                        st.session_state.generated_comic_paths = final_paths
                        st.success("Final comic files generated!")
                        st.rerun()
        st.divider()
