# bluesky_module.py
import os
from dotenv import load_dotenv
from atproto import Client as BlueskyClient, models as bluesky_models
from PIL import Image as PILImageModule

# Load environment variables
load_dotenv()

def load_bluesky_credentials():
    """Loads Bluesky credentials from environment variables."""
    creds = {
        "handle": os.getenv("BLUESKY_HANDLE"),
        "password": os.getenv("BLUESKY_APP_PASSWORD")
    }
    if not all(creds.values()):
        return None
    return creds

def post_comic_to_bluesky(image_path, caption):
    """
    Uploads a single comic image to Bluesky with alt text and a caption.
    """
    credentials = load_bluesky_credentials()
    if not credentials:
        return False, "Bluesky credentials not configured."

    try:
        client = BlueskyClient()
        client.login(credentials["handle"], credentials["password"])

        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            
            with PILImageModule.open(image_path) as img:
                width, height = img.size
            
            upload = client.com.atproto.repo.upload_blob(image_data)
            
            if not upload or not upload.blob:
                return False, "Failed to upload image blob to Bluesky."
            
            # This is the actual content of the post (the "record")
            record_data = {
                "$type": "app.bsky.feed.post",
                "text": caption,
                "createdAt": client.get_current_time_iso(),
                "embed": {
                    "$type": "app.bsky.embed.images",
                    "images": [{
                        "alt": "Gigo Corp Comic Strip",
                        "image": upload.blob,
                        "aspectRatio": {
                            "width": width,
                            "height": height
                        }
                    }]
                }
            }
            
            # FINAL, DEFINITIVE FIX:
            # The function expects a single positional argument, which is a
            # dictionary containing the repo, collection, and record.
            data_to_send = {
                "repo": client.me.did,
                "collection": "app.bsky.feed.post",
                "record": record_data
            }

            response = client.com.atproto.repo.create_record(data_to_send)
            return True, f"Post URI: {response.uri}"

    except Exception as e:
        return False, f"An error occurred with Bluesky: {e}"
