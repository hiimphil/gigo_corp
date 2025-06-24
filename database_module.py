# database_module.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import time
import os # Import os for a more robust check

def init_db():
    """Initializes the Firestore database connection with a robust credential fix."""
    try:
        # Check if running on Streamlit Cloud
        is_streamlit_cloud = hasattr(st, 'secrets')

        if not firebase_admin._apps:
            if not is_streamlit_cloud:
                # Handle local development with a local file if secrets fail
                if os.path.exists('path/to/serviceAccountKey.json'):
                     cred = credentials.Certificate('path/to/serviceAccountKey.json')
                else:
                     st.error("Running locally and service account JSON not found.")
                     return None
            else:
                # --- START OF THE FIX ---
                # The object from st.secrets is immutable. We must create a mutable copy of it first.
                creds_dict = dict(st.secrets["firebase_credentials"])

                # The TOML parser might convert "\n" to a literal "\\n".
                # We will manually replace this in our mutable copy.
                if "private_key" in creds_dict:
                    creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
                # --- END OF THE FIX ---
                
                cred = credentials.Certificate(creds_dict)

            firebase_admin.initialize_app(cred)

        return firestore.client()
        
    except (KeyError, AttributeError):
        st.error("Firebase initialization failed. Please ensure 'firebase_credentials' are correctly set in st.secrets.")
        return None
    except ValueError as e:
        st.error(f"A ValueError occurred during Firebase initialization, likely due to a malformed private key. Error: {e}")
        # Let's print the structure one last time to be sure
        if is_streamlit_cloud and "firebase_credentials" in st.secrets:
            st.code(st.secrets['firebase_credentials'])
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during Firebase initialization: {e}")
        return None


@st.cache_data(ttl=3600)
def load_scripts():
    """Loads all scripts from the Firestore database."""
    db = init_db()
    if db is None:
        return {}
    
    scripts = {}
    try:
        docs = db.collection('scripts').order_by('title').stream()
        for doc in docs:
            script_data = doc.to_dict()
            if 'title' in script_data and 'script_text' in script_data:
                scripts[script_data['title']] = script_data['script_text']
        return scripts
    except Exception as e:
        st.error(f"Error loading scripts from Firestore: {e}")
        return {}

def save_script(title, script_text):
    """Saves or updates a script in the Firestore database."""
    db = init_db()
    if db is None:
        return False, "Database connection not available."
    
    if not title.strip() or not script_text.strip():
        return False, "Title and script cannot be empty."
    
    try:
        doc_ref = db.collection('scripts').document(title)
        doc_ref.set({
            'title': title,
            'script_text': script_text,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        st.cache_data.clear()
        return True, f"Script '{title}' saved successfully."
    except Exception as e:
        return False, f"Error saving script to Firestore: {e}"

def delete_script(title):
    """Deletes a script from the Firestore database by its title."""
    db = init_db()
    if db is None:
        return False, "Database connection not available."
        
    if not title.strip():
        return False, "Title cannot be empty."
        
    try:
        db.collection('scripts').document(title).delete()
        st.cache_data.clear()
        return True, f"Script '{title}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting script from Firestore: {e}"
