# ui_sidebar.py
import streamlit as st
import comic_generator_module
import database_module # Import database_module to call the migration function

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
    
    # --- Temporary Migration Tool ---
    st.sidebar.header("⚙️ Admin Tools")
    if is_admin:
        if st.sidebar.button("Migrate Old Scripts (Run Once)"):
            message = ""
            count = 0
            with st.sidebar.spinner("Migrating scripts..."):
                # Perform the migration first, without drawing any UI inside the spinner
                message, count = database_module.migrate_scripts_collection()
            
            # Now that the spinner is closed, display the results
            if count > 0:
                st.sidebar.success(message)
                st.sidebar.info("You can now remove the migration button code from 'ui_sidebar.py'.")
                st.rerun() # Rerun to refresh the script list in the comic maker
            else:
                st.sidebar.warning(message)
    else:
        st.sidebar.info("Log in to see admin tools.")

    return is_admin
