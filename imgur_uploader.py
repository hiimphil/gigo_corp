# imgur_uploader.py
import requests
import os
from dotenv import load_dotenv
import base64

def load_imgur_credentials():
    # ... (This function remains the same) ...
    load_dotenv()
    creds = {
        "client_id": os.getenv("IMGUR_CLIENT_ID"),
        "client_secret": os.getenv("IMGUR_CLIENT_SECRET"),
        "access_token": os.getenv("IMGUR_ACCESS_TOKEN"),
        "refresh_token": os.getenv("IMGUR_REFRESH_TOKEN")
    }
    if not creds["client_id"] or not creds["access_token"]: return None
    return creds

def refresh_imgur_access_token(refresh_token, client_id, client_secret):
    # ... (This function remains the same) ...
    if not all([refresh_token, client_id, client_secret]): return None
    url = "https://api.imgur.com/oauth2/token"
    payload = {'refresh_token': refresh_token, 'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'refresh_token'}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        data = response.json()
        new_access_token = data.get('access_token'); new_refresh_token = data.get('refresh_token')
        if new_access_token:
            print("Imgur access token refreshed successfully.")
            # IMPORTANT: You need to manually update your .env file with these new tokens!
            return new_access_token, new_refresh_token or refresh_token
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"Error refreshing Imgur token: {e}")
        return None, None

def upload_image_to_imgur(image_path, access_token, title=None, description=None):
    """
    Uploads a single image to Imgur using a provided access token.
    Returns the direct link to the image on success, or raises an exception on failure.
    """
    headers = {'Authorization': f'Bearer {access_token}'}
    with open(image_path, 'rb') as img_file: image_data = img_file.read()
    payload = {'image': base64.b64encode(image_data), 'type': 'base64'}
    if title: payload['title'] = title
    if description: payload['description'] = description
    
    upload_url = "https://api.imgur.com/3/image"
    response = requests.post(upload_url, headers=headers, data=payload)
    response.raise_for_status() # Will raise HTTPError for 4xx/5xx
    data = response.json()

    if data.get('success') and data.get('data') and data['data'].get('link'):
        return data['data']['link']
    else:
        raise Exception(f"Imgur API Error: {data.get('data', {}).get('error', 'Unknown error')}")

def upload_multiple_images_to_imgur(local_image_paths, title_prefix="Gigo Co Comic", description=""):
    """
    Uploads a list of local images to Imgur. Handles token refresh.
    Returns a list of public URLs, or None and an error message if it fails.
    """
    credentials = load_imgur_credentials()
    if not credentials or not credentials["access_token"]:
        return None, "Imgur credentials not fully configured."

    current_access_token = credentials["access_token"]
    public_urls = []

    for i, local_path in enumerate(local_image_paths):
        if not os.path.exists(local_path):
            return None, f"Image file not found: {local_path}"

        try:
            print(f"Uploading image {i+1}/{len(local_image_paths)} to Imgur: {os.path.basename(local_path)}")
            # Construct a unique title for each panel
            img_title = f"{title_prefix} - Panel {i+1}" if i < len(local_image_paths) - 1 else f"{title_prefix} - Composite"
            link = upload_image_to_imgur(local_path, current_access_token, img_title, description)
            public_urls.append(link)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print("Imgur access token may be expired. Attempting to refresh...")
                if credentials["refresh_token"] and credentials["client_id"] and credentials["client_secret"]:
                    new_access_token, new_refresh_token = refresh_imgur_access_token(
                        credentials["refresh_token"], credentials["client_id"], credentials["client_secret"]
                    )
                    if new_access_token:
                        print("Token refreshed. Please manually update your .env file with the new tokens for next time.")
                        print("Retrying upload with new token...")
                        current_access_token = new_access_token # Use new token for subsequent uploads in this session
                        os.environ['IMGUR_ACCESS_TOKEN'] = new_access_token # Update for current process
                        if new_refresh_token: os.environ['IMGUR_REFRESH_TOKEN'] = new_refresh_token
                        try: # Retry the failed upload once
                            link = upload_image_to_imgur(local_path, current_access_token, img_title, description)
                            public_urls.append(link)
                        except Exception as retry_e:
                            return None, f"Imgur upload failed on retry after token refresh: {retry_e}"
                    else:
                        return None, "Failed to refresh Imgur token. Please re-authenticate."
                else:
                    return None, "Imgur token expired, and no refresh token or client secret configured."
            else:
                return None, f"HTTP error during Imgur upload: {e}"
        except Exception as e:
            return None, f"An unexpected error occurred during Imgur upload: {e}"

    if len(public_urls) == len(local_image_paths):
        print("All images uploaded to Imgur successfully.")
        return public_urls, None
    else:
        return None, "An unknown error occurred: not all images were uploaded."

