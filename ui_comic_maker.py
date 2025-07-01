# ui_comic_maker.py
import streamlit as st
import time
import ui_editor  # Contains the editor and comic finalization logic
import ui_social_poster # Contains the social media posting UI

def display(is_admin):
    """
    Renders the entire UI for the Web Comic Maker workflow.
    This function acts as a container for the editor and social poster modules.
    """
    st.header("Web Comic Maker")
    st.write("Create a classic 4-panel Gigo Corp comic strip and post it to your social media accounts.")
    st.divider()

    # Display the editor and comic finalization section
    ui_editor.display_editor(is_admin)

    # Display the social media posting section
    ui_social_poster.display_social_poster(is_admin)
