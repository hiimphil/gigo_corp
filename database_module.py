# database_module.py
import sqlite3
import os

DB_FILE = "script_library.db"

def init_db():
    """Initializes the database and creates the scripts table if it doesn't exist."""
    if os.path.exists(DB_FILE):
        return
        
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                script_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()
        con.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")

def save_script(title, script_text):
    """Saves a script to the database. Overwrites if the title already exists."""
    if not title.strip() or not script_text.strip():
        return False, "Title and script cannot be empty."
    
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        # Use INSERT OR REPLACE to handle existing titles gracefully
        cur.execute("INSERT OR REPLACE INTO scripts (title, script_text) VALUES (?, ?)", (title, script_text))
        con.commit()
        con.close()
        return True, f"Script '{title}' saved successfully."
    except Exception as e:
        return False, f"Error saving script: {e}"

def load_scripts():
    """Loads all scripts from the database, returns a dictionary of {title: script_text}."""
    scripts = {}
    if not os.path.exists(DB_FILE):
        return scripts

    try:
        con = sqlite3.connect(DB_FILE)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("SELECT title, script_text FROM scripts ORDER BY title ASC")
        rows = cur.fetchall()
        con.close()
        for row in rows:
            scripts[row['title']] = row['script_text']
        return scripts
    except Exception as e:
        print(f"Error loading scripts: {e}")
        return scripts

def delete_script(title):
    """Deletes a script from the database by its title."""
    if not title.strip():
        return False, "Title cannot be empty."
    
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("DELETE FROM scripts WHERE title = ?", (title,))
        con.commit()
        con.close()
        return True, f"Script '{title}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting script: {e}"
