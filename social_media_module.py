# social_media_module.py
import os
import requests
from dotenv import load_dotenv
from atproto import Client as BlueskyClient, models as bluesky_models
from PIL import Image as PILImageModule # Import the Image module from Pillow
import tweepy
import time
import praw # Import the Python Reddit API Wrapper

# --- Shared Load Function ---
load_dotenv() 

# --- Bluesky Functions ---
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
    Includes aspect ratio to ensure correct display.
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
            # The create_record function now expects a single object containing
            # the repo, collection, and the record data itself.
            response = client.com.atproto.repo.create_record(
                data={
                    "repo": client.me.did,
                    "collection": bluesky_models.ids.AppBskyFeedPost,
                    "record": record_data
                }
            )
            return True, f"Post URI: {response.uri}"

    except Exception as e:
        return False, f"An error occurred with Bluesky: {e}"


# --- Twitter Functions ---
def load_twitter_credentials():
    """Loads Twitter API v2 credentials."""
    creds = {
        "bearer_token": os.getenv("TWITTER_BEARER_TOKEN"),
        "consumer_key": os.getenv("TWITTER_API_KEY"),
        "consumer_secret": os.getenv("TWITTER_API_KEY_SECRET"),
        "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
        "access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    }
    if not all(creds.values()):
        return None
    return creds

def post_comic_to_twitter(image_path, caption):
    """Posts a single comic image and caption to Twitter using API v2."""
    credentials = load_twitter_credentials()
    if not credentials:
        return False, "Twitter credentials not fully configured."

    try:
        auth_v1 = tweepy.OAuth1UserHandler(
            credentials["consumer_key"], credentials["consumer_secret"],
            credentials["access_token"], credentials["access_token_secret"]
        )
        api_v1 = tweepy.API(auth_v1)
        
        media = api_v1.media_upload(filename=image_path)
        media_id = media.media_id_string
        
        client_v2 = tweepy.Client(
            bearer_token=credentials["bearer_token"],
            consumer_key=credentials["consumer_key"],
            consumer_secret=credentials["consumer_secret"],
            access_token=credentials["access_token"],
            access_token_secret=credentials["access_token_secret"]
        )
        
        response = client_v2.create_tweet(text=caption, media_ids=[media_id])
        tweet_id = response.data['id']
        return True, f"Tweet ID: {tweet_id}"

    except Exception as e:
        return False, f"An error occurred with Twitter: {e}"

# --- Reddit Functions ---
def load_reddit_credentials():
    """Loads Reddit credentials from environment variables."""
    creds = {
        "client_id": os.getenv("REDDIT_CLIENT_ID"),
        "client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
        "user_agent": os.getenv("REDDIT_USER_AGENT"),
        "username": os.getenv("REDDIT_USERNAME"),
        "password": os.getenv("REDDIT_PASSWORD"),
    }
    if not all(creds.values()):
        return None
    return creds

def post_comic_to_reddit(image_path, title, subreddit_name):
    """Uploads a single comic image to a specified subreddit."""
    credentials = load_reddit_credentials()
    if not credentials:
        return False, "Reddit credentials not fully configured."
        
    try:
        reddit = praw.Reddit(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            user_agent=credentials["user_agent"],
            username=credentials["username"],
            password=credentials["password"],
        )
        
        subreddit = reddit.subreddit(subreddit_name)
        submission = subreddit.submit_image(title=title, image_path=image_path)
        
        return True, f"Post URL: {submission.shortlink}"

    except Exception as e:
        return False, f"An error occurred with Reddit: {e}"


# --- Instagram Graph API Configuration & Functions ---
INSTAGRAM_GRAPH_API_VERSION = "v20.0" 

def load_instagram_graph_api_credentials():
    creds = {
        "access_token": os.getenv("INSTAGRAM_GRAPH_API_ACCESS_TOKEN"),
        "business_account_id": os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    }
    if not all(creds.values()): return None
    return creds

def post_carousel_to_instagram_graph_api(image_public_urls, caption):
    """
    Posts a carousel of images (via public URLs) and a caption to Instagram.
    """
    credentials = load_instagram_graph_api_credentials()
    if not credentials:
        return False, "Instagram Graph API credentials not configured."

    ig_user_id = credentials["business_account_id"]
    access_token = credentials["access_token"]
    
    if not image_public_urls or len(image_public_urls) < 2 or len(image_public_urls) > 10:
        return False, f"Invalid number of images for carousel. Got {len(image_public_urls)}, need 2-10."

    child_container_ids = []
    for i, image_url in enumerate(image_public_urls):
        upload_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{ig_user_id}/media"
        upload_params = {'image_url': image_url, 'is_carousel_item': 'true', 'access_token': access_token}
        try:
            response_upload = requests.post(upload_url, params=upload_params)
            response_upload.raise_for_status()
            creation_id = response_upload.json()['id']
            child_container_ids.append(creation_id)
        except requests.exceptions.RequestException as e:
            return False, f"Error creating media container for image {i+1}: {e.response.json() if e.response else e}"

    for i, container_id in enumerate(child_container_ids):
        for _ in range(15):
            status_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{container_id}"
            status_params = {'fields': 'status_code', 'access_token': access_token}
            response_status = requests.get(status_url, params=status_params).json()
            status = response_status.get('status_code')
            if status == 'FINISHED': break
            if status == 'ERROR': return False, f"Error processing container {container_id}. Status: ERROR."
            time.sleep(5)
        else:
            return False, f"Timeout: Container {container_id} was not ready in time."
    
    carousel_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{ig_user_id}/media"
    carousel_params = {
        'caption': caption,
        'media_type': 'CAROUSEL',
        'children': ','.join(child_container_ids),
        'access_token': access_token
    }
    try:
        response_carousel = requests.post(carousel_url, params=carousel_params)
        response_carousel.raise_for_status()
        carousel_container_id = response_carousel.json()['id']
    except requests.exceptions.RequestException as e:
        return False, f"Error creating main carousel container: {e.response.json() if e.response else e}"

    publish_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    publish_params = {'creation_id': carousel_container_id, 'access_token': access_token}
    try:
        response_publish = requests.post(publish_url, params=publish_params)
        response_publish.raise_for_status()
        published_media_id = response_publish.json().get('id')
        if published_media_id:
            permalink_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{published_media_id}?fields=permalink&access_token={access_token}"
            permalink_response = requests.get(permalink_url).json()
            permalink = permalink_response.get('permalink', f"Post ID: {published_media_id}")
            return True, permalink
        else:
            return False, f"Failed to publish carousel. Response: {response_publish.json()}"
    except requests.exceptions.RequestException as e:
        return False, f"Error publishing carousel container: {e.response.json() if e.response else e}"
