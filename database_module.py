# database_module.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import time

# This function will initialize the Firebase connection.
# It uses st.secrets to get the credentials, which is ideal for Streamlit Cloud.
def init_db():
    """Initializes the Firestore database connection."""
    try:
        # Check if the app is already initialized to prevent errors on rerun
        if not firebase_admin._apps:
            # Get the credentials from Streamlit's secrets management
            # The user needs to set this up in their Streamlit Cloud settings
            creds_dict = st.secrets["firebase_credentials"]
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except (KeyError, ValueError) as e:
        # Provide a helpful error message if secrets are not set or are malformed
        st.error("Firebase initialization failed. Please ensure 'firebase_credentials' are correctly set in st.secrets.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during Firebase initialization: {e}")
        return None

# Use st.cache_data to cache the script list. This prevents re-fetching from Firestore on every single interaction.
# The cache will be cleared when we save or delete a script.
@st.cache_data(ttl=3600) # Cache for 1 hour or until cleared
def load_scripts():
    """Loads all scripts from the Firestore database, returns a dictionary of {title: script_text}."""
    db = init_db()
    if db is None:
        return {}
    
    scripts = {}
    try:
        # Access the 'scripts' collection, order by title, and stream the documents
        docs = db.collection('scripts').order_by('title').stream()
        for doc in docs:
            script_data = doc.to_dict()
            # Ensure both title and script_text exist before adding
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
        # Use the script's title as the document ID for easy lookup and overwriting.
        # The .set() method creates the document if it doesn't exist, or overwrites it if it does.
        doc_ref = db.collection('scripts').document(title)
        doc_ref.set({
            'title': title,
            'script_text': script_text,
            'created_at': firestore.SERVER_TIMESTAMP # Store a server-side timestamp
        })
        # Important: Clear the cache so the script list is reloaded with the new data.
        st.cache_data.clear()
        return True, f"Script '{title}' saved successfully to Firestore."
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
        # Delete the document with the given title (which is its ID).
        db.collection('scripts').document(title).delete()
        # Important: Clear the cache so the script list is reloaded.
        st.cache_data.clear()
        return True, f"Script '{title}' deleted successfully from Firestore."
    except Exception as e:
        return False, f"Error deleting script from Firestore: {e}"
