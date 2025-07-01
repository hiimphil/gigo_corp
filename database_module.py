# database_module.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

def init_db():
    """Initializes the Firestore database connection."""
    try:
        if not firebase_admin._apps:
            creds_dict = dict(st.secrets["firebase_credentials"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")
        return None

@st.cache_data(ttl=3600)
def load_scripts(collection_name):
    """Loads all scripts from a specified Firestore collection."""
    db = init_db()
    if db is None: return {}
    
    scripts = {}
    try:
        docs = db.collection(collection_name).order_by('title').stream()
        for doc in docs:
            script_data = doc.to_dict()
            if 'title' in script_data and 'script_text' in script_data:
                scripts[script_data['title']] = script_data['script_text']
        return scripts
    except Exception as e:
        st.error(f"Error loading scripts from '{collection_name}': {e}")
        return {}

def save_script(title, script_text, collection_name):
    """Saves or updates a script in a specified Firestore collection."""
    db = init_db()
    if db is None: return False, "Database connection not available."
    if not title.strip() or not script_text.strip():
        return False, "Title and script cannot be empty."
    
    try:
        doc_ref = db.collection(collection_name).document(title)
        doc_ref.set({
            'title': title,
            'script_text': script_text,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        load_scripts.clear(collection_name=collection_name)
        return True, f"Script '{title}' saved successfully."
    except Exception as e:
        return False, f"Error saving script: {e}"

def delete_script(title, collection_name):
    """Deletes a script from a specified Firestore collection."""
    db = init_db()
    if db is None: return False, "Database connection not available."
    if not title.strip(): return False, "Title cannot be empty."
        
    try:
        db.collection(collection_name).document(title).delete()
        load_scripts.clear(collection_name=collection_name)
        return True, f"Script '{title}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting script: {e}"

def migrate_scripts_collection():
    """
    Reads all documents from the old 'scripts' collection and copies them
    to the new 'comic_scripts' collection.
    """
    db = init_db()
    if not db:
        return "Database connection failed.", 0

    source_collection = "scripts"
    dest_collection = "comic_scripts"
    
    source_ref = db.collection(source_collection)
    dest_ref = db.collection(dest_collection)

    try:
        docs = source_ref.stream()
        doc_list = list(docs)
        if not doc_list:
            return f"No documents found in '{source_collection}'. Nothing to migrate.", 0
        
        count = 0
        for doc in doc_list:
            doc_id = doc.id
            doc_data = doc.to_dict()
            # Set the data in the new collection. This will create or overwrite.
            dest_ref.document(doc_id).set(doc_data)
            count += 1
        
        # Clear the cache for the comic scripts so the list refreshes
        load_scripts.clear(collection_name=dest_collection)
        
        return f"Migration complete! Moved {count} documents to '{dest_collection}'.", count
    except Exception as e:
        return f"An error occurred during migration: {e}", 0
