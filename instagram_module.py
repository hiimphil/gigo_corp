# instagram_module.py
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

INSTAGRAM_GRAPH_API_VERSION = "v20.0" 

def load_instagram_graph_api_credentials():
    """Loads Instagram Graph API credentials from environment variables."""
    creds = {
        "access_token": os.getenv("INSTAGRAM_GRAPH_API_ACCESS_TOKEN"),
        "business_account_id": os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    }
    if not all(creds.values()): 
        return None
    return creds

def post_carousel_to_instagram_graph_api(image_public_urls, caption):
    """
    Posts a carousel of images (via public URLs) and a caption to Instagram.
    Returns a tuple of (bool, str) for success and a message.
    """
    credentials = load_instagram_graph_api_credentials()
    if not credentials:
        return False, "Instagram Graph API credentials not fully configured."

    ig_user_id = credentials["business_account_id"]
    access_token = credentials["access_token"]
    
    if not image_public_urls or len(image_public_urls) < 2 or len(image_public_urls) > 10:
        return False, f"Invalid number of images for carousel. Got {len(image_public_urls)}, need 2-10."

    # Step 1: Upload each image and get a container ID for it.
    child_container_ids = []
    for i, image_url in enumerate(image_public_urls):
        upload_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{ig_user_id}/media"
        upload_params = {'image_url': image_url, 'is_carousel_item': 'true', 'access_token': access_token}
        try:
            print(f"IG Upload: Creating container for image {i+1}...")
            response_upload = requests.post(upload_url, params=upload_params)
            response_upload.raise_for_status()
            creation_id = response_upload.json()['id']
            child_container_ids.append(creation_id)
        except requests.exceptions.RequestException as e:
            error_details = e.response.json() if e.response else str(e)
            print(f"IG Upload Error (Step 1): {error_details}")
            return False, f"Error creating media container for image {i+1}: {error_details}"

    # Step 2: Poll the status of each container until it's FINISHED.
    for i, container_id in enumerate(child_container_ids):
        for _ in range(15):
            print(f"IG Upload: Checking status for container {i+1}...")
            status_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{container_id}"
            status_params = {'fields': 'status_code', 'access_token': access_token}
            response_status = requests.get(status_url, params=status_params).json()
            status = response_status.get('status_code')
            if status == 'FINISHED':
                print(f"Container {i+1} is FINISHED.")
                break
            if status == 'ERROR':
                print(f"IG Upload Error (Step 2): Container {container_id} status is ERROR.")
                return False, f"Error processing container {container_id}. Status: ERROR."
            time.sleep(5)
        else:
            print(f"IG Upload Error (Step 2): Timeout for container {container_id}.")
            return False, f"Timeout: Container {container_id} was not ready in time."
    
    # Step 3: Create the main carousel container.
    carousel_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{ig_user_id}/media"
    carousel_params = {
        'caption': caption,
        'media_type': 'CAROUSEL',
        'children': ','.join(child_container_ids),
        'access_token': access_token
    }
    try:
        print("IG Upload: Creating main carousel container...")
        response_carousel = requests.post(carousel_url, params=carousel_params)
        response_carousel.raise_for_status()
        carousel_container_id = response_carousel.json()['id']
    except requests.exceptions.RequestException as e:
        error_details = e.response.json() if e.response else str(e)
        print(f"IG Upload Error (Step 3): {error_details}")
        return False, f"Error creating main carousel container: {error_details}"

    # Step 4: Publish the carousel.
    publish_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    publish_params = {'creation_id': carousel_container_id, 'access_token': access_token}
    try:
        print("IG Upload: Publishing carousel...")
        response_publish = requests.post(publish_url, params=publish_params)
        response_publish.raise_for_status()
        published_media_id = response_publish.json().get('id')
        if published_media_id:
            permalink_url = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_API_VERSION}/{published_media_id}?fields=permalink&access_token={access_token}"
            permalink_response = requests.get(permalink_url).json()
            permalink = permalink_response.get('permalink', f"Post ID: {published_media_id}")
            return True, permalink
        else:
            print(f"IG Upload Error (Step 4): Failed to get media ID. Response: {response_publish.json()}")
            return False, f"Failed to publish carousel. Response: {response_publish.json()}"
    except requests.exceptions.RequestException as e:
        error_details = e.response.json() if e.response else str(e)
        print(f"IG Upload Error (Step 4): {error_details}")
        return False, f"Error publishing carousel container: {error_details}"
