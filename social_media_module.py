# social_media_module.py
import os
import requests
from dotenv import load_dotenv
import tweepy
import praw # Import the Python Reddit API Wrapper

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
