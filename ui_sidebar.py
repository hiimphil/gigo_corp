# ui_sidebar.py
import streamlit as st
import time
import comic_generator_module
import database_module

def check_password():
    """Returns `True` if the user has the correct password."""
    try:
        password = st.sidebar.text_input("Enter Password for Admin Access", type="password")
        if "APP_PASSWORD" in st.secrets and password == st.secrets.get("APP_PASSWORD"):
            return True
        elif "APP_PASSWORD" not in st.secrets and password == "localpass":
             st.sidebar.info("Using local password. Set APP_PASSWORD secret for deployment.")
             return True
        elif password:
            st.sidebar.warning("Incorrect password.")
            return False
        else:
            return False
    except Exception:
        st.sidebar.info("Password feature disabled. For local dev, you can set a fallback.")
        return True

def display_sidebar():
    """Renders the entire sidebar and returns the admin status."""
    st.sidebar.header("🔑 Admin Access")
    is_admin = check_password()
    st.sidebar.divider()

    st.sidebar.header("🎨 Action Guide")
    st.sidebar.write("Use `(action)` or `(direction)` in a script line.")
    st.sidebar.code("A:(left) Hi!\nB:(shocked) Hello.")
    
    available_actions = comic_generator_module.get_available_actions()
    if available_actions:
        for char, states in available_actions.items():
            with st.sidebar.expander(f"Character {char.upper()} Actions"):
                for state, directions in states.items():
                    st.write(f"**{state.capitalize()}:**")
                    for direction, actions in directions.items():
                        if actions:
                            st.write(f"- _{direction.capitalize()}_: {', '.join(actions)}")
    else:
        st.sidebar.info("No action folders found in your 'Images' directory.")
    
    st.sidebar.divider()

    st.sidebar.header("📜 Script Library")
    saved_scripts = database_module.load_scripts() 
    if saved_scripts:
        script_to_load = st.sidebar.selectbox(
            "Select a script:", 
            options=list(saved_scripts.keys()), 
            index=None, 
            placeholder="-- Choose a script to load --"
        )
        load_col, delete_col = st.sidebar.columns(2)
        with load_col:
            if st.button("Load Script", use_container_width=True):
                if script_to_load:
                    st.session_state.current_script = saved_scripts[script_to_load]
                    st.session_state.script_title = script_to_load
                    st.rerun()
        with delete_col:
            if st.button("Delete", use_container_width=True):
                if script_to_load and is_admin:
                    success, message = database_module.delete_script(script_to_load)
                    st.toast(message, icon="🗑️" if success else "❌")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.sidebar.warning("Select a script and be an admin.")
    else:
        st.sidebar.write("No saved scripts in Firestore yet.")

    return is_admin
