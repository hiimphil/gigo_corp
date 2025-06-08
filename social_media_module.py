# social_media_module.py
import os
import requests
from dotenv import load_dotenv
from atproto import Client as BlueskyClient, models as bluesky_models
from PIL import Image as PILImageModule
import tweepy
import time

# --- Shared Load Function ---
load_dotenv() 

# --- BLUESKY ---
# --- Bluesky Configuration & Functions ---
BLUESKY_SESSION_FILE_PATH = "bluesky_session.json" 

def load_bluesky_credentials():
    creds = {
        "handle": os.getenv("BLUESKY_HANDLE"),
        "app_password": os.getenv("BLUESKY_APP_PASSWORD"),
    }
    if not all(creds.values()): return None
    return creds

def get_bluesky_client():
    credentials = load_bluesky_credentials()
    if not credentials: return None, "Bluesky credentials not configured."
    try:
        client = BlueskyClient()
        profile = client.login(credentials["handle"], credentials["app_password"])
        print(f"Successfully logged into Bluesky as {profile.handle}")
        return client, None
    except Exception as e:
        return None, f"Bluesky login failed: {e}"

def post_comic_to_bluesky(image_path, caption):
    client, error_msg = get_bluesky_client()
    if error_msg: return False, error_msg
    if not os.path.exists(image_path): return False, f"Image file not found at: {image_path}"
    try:
        with open(image_path, 'rb') as f: img_bytes = f.read()
        upload = client.com.atproto.repo.upload_blob(img_bytes)
        embed_images = bluesky_models.AppBskyEmbedImages.Main(
            images=[bluesky_models.AppBskyEmbedImages.Image(alt=caption[:100], image=upload.blob)]
        )
        post_record = client.send_post(text=caption, embed=embed_images)
        if post_record and post_record.uri:
            web_url = f"https://bsky.app/profile/{client.me.handle}/post/{post_record.uri.rsplit('/', 1)[-1]}"
            return True, web_url
        return False, f"Failed to send post to Bluesky. Response: {post_record}"
    except Exception as e:
        return False, f"An unexpected error during Bluesky post: {type(e).__name__} - {e}"

# --- Twitter Configuration & Functions ---
def load_twitter_credentials():
    creds = {
        "consumer_key": os.getenv("TWITTER_CONSUMER_KEY"),
        "consumer_secret": os.getenv("TWITTER_CONSUMER_SECRET"),
        "access_token": os.getenv("TWITTER_ACCESS_TOKEN"),
        "access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        "bearer_token": os.getenv("TWITTER_BEARER_TOKEN")
    }
    if not all(value is not None for key, value in creds.items() if key != "bearer_token"): return None
    if not creds["bearer_token"]: return None # Bearer token is essential for v2 client
    return creds

def post_comic_to_twitter(image_path, caption):
    credentials = load_twitter_credentials()
    if not credentials: return False, "Twitter API credentials not fully configured."
    if not os.path.exists(image_path): return False, f"Image file not found at: {image_path}"
    try:
        auth_v1 = tweepy.OAuth1UserHandler(
            credentials["consumer_key"], credentials["consumer_secret"],
            credentials["access_token"], credentials["access_token_secret"]
        )
        api_v1 = tweepy.API(auth_v1)
        media = api_v1.media_upload(filename=image_path)
        client_v2 = tweepy.Client(
            bearer_token=credentials["bearer_token"], consumer_key=credentials["consumer_key"],
            consumer_secret=credentials["consumer_secret"], access_token=credentials["access_token"],
            access_token_secret=credentials["access_token_secret"], wait_on_rate_limit=True
        )
        response = client_v2.create_tweet(text=caption, media_ids=[media.media_id_string])
        tweet_data = response.data
        if tweet_data and 'id' in tweet_data:
            tweet_id = tweet_data['id']
            tweet_url = f"https://twitter.com/placeholder_user/status/{tweet_id}" 
            return True, tweet_url
        return False, f"Failed to post tweet. Response: {response.errors if hasattr(response, 'errors') else response}"
    except Exception as e:
        return False, f"An error occurred during Twitter post: {type(e).__name__} - {e}"


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
    Returns (True, post_permalink) on success, or (False, error_message) on failure.
    """
    credentials = load_instagram_graph_api_credentials()
    if not credentials:
        return False, "Instagram Graph API credentials not configured."

    ig_user_id = credentials["business_account_id"]
    access_token = credentials["access_token"]
    
    if not image_public_urls or len(image_public_urls) < 2 or len(image_public_urls) > 10:
        return False, f"Invalid number of images for carousel. Got {len(image_public_urls)}, need 2-10."

    # Step 1: Upload each image and get a container ID for it.
    child_container_ids = []
    for i, image_url in enumerate(image_public_urls):
        print(f"Step 1.{i+1}: Uploading image {i+1} to create a media container...")
        upload_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{ig_user_id}/media"
        upload_params = {'image_url': image_url, 'is_carousel_item': 'true', 'access_token': access_token}
        try:
            response_upload = requests.post(upload_url, params=upload_params)
            response_upload.raise_for_status()
            creation_id = response_upload.json()['id']
            print(f"  > Container created for image {i+1}: {creation_id}")
            child_container_ids.append(creation_id)
        except requests.exceptions.RequestException as e:
            return False, f"Error creating media container for image {i+1}: {e.response.json() if e.response else e}"

    # Step 2: Poll the status of each container until it's FINISHED.
    print("\nStep 2: Checking status of all media containers...")
    for i, container_id in enumerate(child_container_ids):
        for _ in range(15):  # Poll up to 15 times (e.g., 15 * 5s = 75s timeout)
            status_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{container_id}"
            status_params = {'fields': 'status_code', 'access_token': access_token}
            response_status = requests.get(status_url, params=status_params).json()
            status = response_status.get('status_code')
            print(f"  > Status for container {i+1} ({container_id}): {status}")
            if status == 'FINISHED': break
            if status == 'ERROR': return False, f"Error processing container {container_id}. Status: ERROR."
            time.sleep(5)  # Wait 5 seconds before polling again
        else: # This 'else' belongs to the 'for' loop, it runs if the loop completes without a 'break'
            return False, f"Timeout: Container {container_id} was not ready in time."
    
    print("  > All media containers are ready.")

    # Step 3: Create the main carousel container.
    print("\nStep 3: Creating main carousel container...")
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
        print(f"  > Main carousel container created: {carousel_container_id}")
    except requests.exceptions.RequestException as e:
        return False, f"Error creating main carousel container: {e.response.json() if e.response else e}"

    # Step 4: Publish the carousel.
    print("\nStep 4: Publishing carousel container...")
    publish_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    publish_params = {'creation_id': carousel_container_id, 'access_token': access_token}
    try:
        response_publish = requests.post(publish_url, params=publish_params)
        response_publish.raise_for_status()
        publish_result = response_publish.json()
        published_media_id = publish_result.get('id')
        if published_media_id:
            print(f"  > Carousel published successfully! Media ID: {published_media_id}")
            # Getting the permalink requires another API call.
            permalink_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{published_media_id}?fields=permalink&access_token={access_token}"
            permalink_response = requests.get(permalink_url).json()
            permalink = permalink_response.get('permalink', f"Post ID: {published_media_id}")
            return True, permalink
        else:
            return False, f"Failed to publish carousel. Response: {publish_result}"
    except requests.exceptions.RequestException as e:
        return False, f"Error publishing carousel container: {e.response.json() if e.response else e}"
    
if __name__ == '__main__':
    # Test Bluesky (if configured)
    print("Testing Bluesky posting module...")
    # ... (Bluesky test code as before) ...

    # Test Twitter (if configured)
    print("\nTesting Twitter posting module...")
    # ... (Twitter test code as before) ...
    
    # Test Instagram Graph API (if configured)
    print("\nTesting Instagram Graph API posting module...")
    # IMPORTANT: You need a PUBLICLY ACCESSIBLE URL for an image for this test.
    # Replace with a real public image URL for testing.
    # Example: test_image_public_url = "https://www.python.org/static/community_logos/python-logo-master-v3-TM.png"
    test_image_public_url = input("Enter a PUBLIC image URL for Instagram test (or leave blank to skip): ").strip()
    
    if test_image_public_url:
        test_ig_caption = "Testing Instagram Graph API with a #Python logo! 🤖 #GraphAPI #Automation"
        ig_success, ig_message = post_comic_to_instagram_graph_api(test_image_public_url, test_ig_caption)
        print(f"Instagram Graph API Test: Success={ig_success}, Message={ig_message}")
    else:
        print("Skipping Instagram Graph API test as no public image URL was provided.")
