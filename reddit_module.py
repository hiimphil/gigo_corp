# reddit_module.py
import os
from dotenv import load_dotenv
import praw

# Load environment variables
load_dotenv()

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
    """
    Uploads a single comic image to a specified subreddit.
    Returns a tuple of (success_boolean, message_string).
    """
    credentials = load_reddit_credentials()
    if not credentials:
        return False, "Reddit credentials not fully configured in your .env file."
        
    if not os.path.exists(image_path):
        return False, f"Image file not found at path: {image_path}"

    try:
        # Initialize the PRAW instance
        reddit = praw.Reddit(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            user_agent=credentials["user_agent"],
            username=credentials["username"],
            password=credentials["password"],
            check_for_async=False # Add this for compatibility in some environments
        )
        
        # Verify that authentication was successful and the user is not read-only
        if reddit.read_only:
            return False, "Authentication failed. Reddit connection is in read-only mode. Check credentials."

        # Get the subreddit and submit the image
        subreddit = reddit.subreddit(subreddit_name)
        submission = subreddit.submit_image(title=title, image_path=image_path, timeout=60)
        
        # Return the success status and the URL of the new post
        return True, f"Post URL: {submission.shortlink}"

    except praw.exceptions.PRAWException as e:
        # Catch specific PRAW errors for better feedback
        return False, f"A Reddit-specific error occurred: {e}"
    except Exception as e:
        # Catch any other general exceptions
        return False, f"An unexpected error occurred with Reddit: {e}"
