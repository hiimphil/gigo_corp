# database_module.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
import time
import hashlib

def init_db():
    """Initializes the Firestore and Firebase Storage services."""
    try:
        if not firebase_admin._apps:
            creds_dict = dict(st.secrets["firebase_credentials"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')
            
            # Get the storage bucket URL from secrets
            storage_bucket_url = st.secrets.get("firebase_storage", {}).get("bucket_url")
            if not storage_bucket_url:
                st.error("Firebase Storage bucket URL not found in secrets. Please add `[firebase_storage]` section with `bucket_url`.")
                return None, None

            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred, {
                'storageBucket': storage_bucket_url
            })
        
        db = firestore.client()
        bucket = storage.bucket()
        return db, bucket
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")
        return None, None

@st.cache_data(ttl=3600)
def load_scripts(collection_name):
    """Loads all scripts from a specified Firestore collection."""
    db, _ = init_db()
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
    db, _ = init_db()
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
    db, _ = init_db()
    if db is None: return False, "Database connection not available."
    if not title.strip(): return False, "Title cannot be empty."
        
    try:
        db.collection(collection_name).document(title).delete()
        load_scripts.clear(collection_name=collection_name)
        return True, f"Script '{title}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting script: {e}"

# --- New Functions for Audio Caching ---

def get_audio_cache_entry(text_hash):
    """Checks Firestore for a cached audio file URL."""
    db, _ = init_db()
    if not db: return None
    
    try:
        doc_ref = db.collection("audio_cache").document(text_hash)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get("download_url")
        return None
    except Exception as e:
        print(f"Error checking audio cache: {e}")
        return None

def set_audio_cache_entry(text_hash, download_url, text):
    """Saves a new audio file URL to the Firestore cache."""
    db, _ = init_db()
    if not db: return
    
    try:
        doc_ref = db.collection("audio_cache").document(text_hash)
        doc_ref.set({
            "download_url": download_url,
            "original_text": text,
            "created_at": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error setting audio cache entry: {e}")

def upload_audio_to_storage(source_file_path, text_hash):
    """Uploads a local audio file to Firebase Storage and returns its public URL."""
    _, bucket = init_db()
    if not bucket: return None, "Firebase Storage bucket not available."
    
    destination_blob_name = f"audio_cache/{text_hash}.mp3"
    blob = bucket.blob(destination_blob_name)
    
    try:
        blob.upload_from_filename(source_file_path)
        # Make the blob publicly viewable and get the URL
        blob.make_public()
        return blob.public_url, None
    except Exception as e:
        return None, f"Failed to upload to Firebase Storage: {e}"
