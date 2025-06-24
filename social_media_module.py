# social_media_module.py
import os
import requests
from dotenv import load_dotenv
import tweepy

# --- Shared Load Function ---
load_dotenv() 

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
        # V1 API client for media upload
        auth_v1 = tweepy.OAuth1UserHandler(
            credentials["consumer_key"], credentials["consumer_secret"],
            credentials["access_token"], credentials["access_token_secret"]
        )
        api_v1 = tweepy.API(auth_v1)
        
        media = api_v1.media_upload(filename=image_path)
        media_id = media.media_id_string
        
        # V2 API client for creating the tweet
        client_v2 = tweepy.Client(
            bearer_token=credentials["bearer_token"],
            consumer_key=credentials["consumer_key"],
            consumer_secret=credentials["consumer_secret"],
            access_token=credentials["access_token"],
            access_token_secret=credentials["access_token_secret"]
        )
        
        response = client_v2.create_tweet(text=caption, media_ids=[media_id])
        tweet_id = response.data['id']
        return True, f"https://twitter.com/user/status/{tweet_id}"

    except Exception as e:
        return False, f"An error occurred with Twitter: {e}"

# Note: Reddit functions have been moved to reddit_module.py
