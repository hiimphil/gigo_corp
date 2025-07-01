# ui_sidebar.py
import streamlit as st
import comic_generator_module

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
    """Renders the sidebar for Admin Access and the Action Guide."""
    st.sidebar.header("🔑 Admin Access")
    is_admin = check_password()
    st.sidebar.divider()

    st.sidebar.header("🎨 Visual Action Guide")
    st.sidebar.write("Use `(action)` to change character art.")
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
    st.sidebar.divider()
    st.sidebar.divider()
    st.sidebar.divider()
    st.sidebar.divider()
    st.sidebar.divider()

    # --- NEW: Performance Note Guide ---
    st.sidebar.header("🎤 Performance Note Guide")
    st.sidebar.write("Use `[note]` to add performance or sound effects. The text in brackets will NOT be spoken.")
    with st.sidebar.expander("View Available Notes"):
        st.markdown("""
        **Vocal Delivery:**
        * `[laughs]`
        * `[whispers]`
        * `[sighs]`
        * `[sarcastic]`
        * `[curious]`
        * `[excited]`
        * `[crying]`
        
        **Sound Effects:**
        * `[gunshot]`
        * `[applause]`
        * `[swallows]`
        """)

    return is_admin
