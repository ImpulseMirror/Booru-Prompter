import json
import requests
import time
import argparse
from datetime import datetime, timedelta
from collections import Counter
from config import BOORU_API_URL, TAG_API_URL, API_KEY, USER_ID, SERIES_LIST

# Ensure API key is available before proceeding
if not API_KEY or not USER_ID:
    raise ValueError("API_KEY and USER_ID must be set in config_secret.py")

# Get date range for the last two weeks (Unix timestamp)
two_weeks_ago = int((datetime.now() - timedelta(days=14)).timestamp())

def make_request(url, params, retries=3, rate_limited=True):
    """Make a request with retries and rate limit handling."""
    for i in range(retries):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [403, 429]:  # Rate limit hit
                wait_time = (2 ** i)  # Exponential backoff
                print(f"Rate limit hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
    
    return None  # Return None if all retries fail

def verify_character(tag_name):
    """Check if a tag is an actual character (type=4) using the Gelbooru Tag API."""
    params = {
        "name": tag_name,
        "json": 1,
        "api_key": API_KEY,
        "user_id": USER_ID
    }
    data = make_request(TAG_API_URL, params)

    if data and isinstance(data, list) and data:
        for tag_info in data:
            if tag_info.get("type") == 4:  # Type 4 = character
                return True
    return False

def fetch_series_images(series_name, rate_limited=True):
    """Fetch all images for a given series from the last two weeks."""
    images = []
    page = 0

    while True:
        params = {
            "tags": f"{series_name}",
            "limit": 100,
            "pid": page,
            "json": 1,
            "api_key": API_KEY,
            "user_id": USER_ID
        }

        data = make_request(BOORU_API_URL, params, rate_limited=rate_limited)
        if not data or "post" not in data:
            break  # No more posts available

        sorted_posts = sorted(data["post"], key=lambda x: int(x.get("change", 0)), reverse=True)
        images.extend(sorted_posts)

        # Check if the oldest post in this batch is older than 2 weeks
        oldest_post_date = int(sorted_posts[-1].get("change", 0))
        if oldest_post_date < two_weeks_ago:
            break  # Stop fetching older images

        page += 1

    return images

def extract_top_characters(images):
    """Extract the top 5 most common character tags from images."""
    tag_counter = Counter()
    
    for img in images:
        tags = img.get("tags", "").split()
        for tag in tags:
            formatted_tag = tag.lower().replace(" ", "_")
            tag_counter[formatted_tag] += 1  # Count occurrences

    # Filter valid character names before selecting the top 5
    valid_characters = {tag for tag in tag_counter if verify_character(tag)}

    top_characters = [char for char, _ in tag_counter.most_common(10) if char in valid_characters][:5]

    return top_characters

def fetch_character_images(character_name, rate_limited=True):
    """Fetch images for a specific character from the last two weeks."""
    images = []
    page = 0

    while True:
        params = {
            "tags": f"{character_name}",
            "limit": 100,
            "pid": page,
            "json": 1,
            "api_key": API_KEY,
            "user_id": USER_ID
        }

        data = make_request(BOORU_API_URL, params, rate_limited=rate_limited)
        if not data or "post" not in data:
            break
        
        sorted_posts = sorted(data["post"], key=lambda x: int(x.get("change", 0)), reverse=True)
        images.extend(sorted_posts)

        # Check if the oldest post is older than 2 weeks
        oldest_post_date = int(sorted_posts[-1].get("change", 0))
        if oldest_post_date < two_weeks_ago:
            break

        page += 1

    return images

def process_series_data(rate_limited=True):
    """Fetch and process character data dynamically for each series."""
    results = []

    for series in SERIES_LIST:
        print(f"Processing series: {series}")

        images = fetch_series_images(series, rate_limited)
        if not images:
            print(f"No recent images found for {series}")
            continue

        top_characters = extract_top_characters(images)
        print(f"Top characters for {series}: {top_characters}")

        for character in top_characters:
            char_images = fetch_character_images(character, rate_limited)
            if not char_images:
                continue

            tags = set()
            for img in char_images:
                tags.update(img.get("tags", "").split())

            results.append({
                "character_name": character,
                "series_name": series,
                "num_images_found": len(char_images),
                "aggregated_tags": list(tags)
            })

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch gacha character images from Booru.")
    parser.add_argument("--fast", action="store_true", help="Disable rate limiting for faster requests.")
    
    args = parser.parse_args()
    rate_limited = not args.fast  # Default is True (rate-limited mode)

    character_data = process_series_data(rate_limited)
    output_file = "booru_gacha_results.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(character_data, f, indent=4)

    print(f"Results saved to {output_file}")