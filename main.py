import json
import requests
import time
import argparse
import json
import os
from datetime import datetime, timedelta
from collections import Counter
from config import BOORU_API_URL, TAG_API_URL, API_KEY, USER_ID, SERIES_LIST
from config import IMAGE_FILTER_DAYS

# Global flag to determine whether the script is running in test mode
TEST_MODE = False  
TAG_DIR = "tags"
KNOWN_TAGS_FILE = os.path.join(TAG_DIR, "known_tags.json")
# Ensure the directory exists
os.makedirs(TAG_DIR, exist_ok=True)

# Ensure API key is available before proceeding
if not API_KEY or not USER_ID:
    raise ValueError("API_KEY and USER_ID must be set in config_secret.py")

# Get date range for the last two weeks (Unix timestamp)
filter_day_range = int((datetime.now() - timedelta(days=IMAGE_FILTER_DAYS)).timestamp())

def make_request(url, params, retries=3, rate_limited=True):
    """Make a request with retries and rate limit handling."""
    for i in range(retries):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [403, 429]:  # Rate limit hit
                wait_time = (2 ** i)  # Exponential backoff
                time.sleep(wait_time)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
    
    return None  # Return None if all retries fail

def load_known_tags():
    """Load known character and other tags from JSON."""
    if os.path.exists(KNOWN_TAGS_FILE):
        with open(KNOWN_TAGS_FILE, "r") as f:
            return json.load(f)
    return {"character_tags": [], "other_tags": []}  # Default structure

def save_known_tags(tags_data):
    """Save updated known tags to JSON."""
    with open(KNOWN_TAGS_FILE, "w") as f:
        json.dump(tags_data, f, indent=4)

def verify_character(tag):
    """Check if a tag is a character, using cached results to reduce API calls."""
    tags_data = load_known_tags()

    # Check if tag is already cached
    if tag in tags_data["character_tags"]:
        return True
    if tag in tags_data["other_tags"]:
        return False

    # If not cached, request tag information
    params = {"name": tag, "json": 1}
    data = make_request(TAG_API_URL, params)

    print(f"{data}")
    if not data or not data.get("tag"):
        tags_data["other_tags"].append(tag)
        save_known_tags(tags_data)
        return False

    for tag_data in data.get("tag"):
        print(f"{tags_data}")
        if tag_data["name"] == tag and tag_data.get("type") == 4:  # Character type
            tags_data["character_tags"].append(tag)
            save_known_tags(tags_data)
            return True

    # If not found as a character, save as a non-character
    tags_data["other_tags"].append(tag)
    save_known_tags(tags_data)
    return False

def fetch_series_images(series_name, rate_limited=True):
    """Fetch all images for a given series from the last two weeks."""
    images = []
    page = 0
    last_page_count = None  # Track previous page count to detect repeated pages

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

        # Dynamically compute "filter_day_range" based on the mocked datetime in tests
        current_time = datetime.now().timestamp()
        dynamic_filter_day_range = int(current_time - (IMAGE_FILTER_DAYS * 24 * 60 * 60))  # IMAGE_FILTER_DAYS days ago

        filtered_posts = [img for img in sorted_posts if int(img.get("change", 0)) > dynamic_filter_day_range]

        if not filtered_posts or last_page_count == len(filtered_posts):
            break  # Stop if no new images are being added

        images.extend(filtered_posts)
        last_page_count = len(filtered_posts)  # Update last page count
        page += 1

    return images

def normalize_tag(tag):
    return tag.lower().replace(" ", "_")

def extract_top_characters(images):
    """Extract the top 5 most common character tags from images."""
    tag_counter = Counter()
    for img in images:
        tags = img.get("tags", "").split()
        for tag in tags:
            formatted_tag = normalize_tag(tag)
            tag_counter[formatted_tag] += 1  # Count occurrences

    # Filter valid character names before selecting the top 5
    valid_characters = {normalize_tag(tag) for tag in tag_counter if verify_character(tag)}
    # Normalize valid characters and tag counter keys
    normalized_valid_characters = {normalize_tag(tag) for tag in valid_characters}
    normalized_tag_counter = {normalize_tag(tag): count for tag, count in tag_counter.items()}

    top_characters = []
    sorted_tags = sorted(normalized_tag_counter.items(), key=lambda x: x[1], reverse=True)

    for tag_tuple in sorted_tags:
        tag = tag_tuple[0]  # Extract the tag name (ignore count)
        
        if tag in normalized_valid_characters:
            top_characters.append(tag)

        if len(top_characters) >= 5:  # Stop after selecting top 5
            break
    print(f"DEBUG: Top Characters: {top_characters}")
    print(f"Top: {top_characters}")

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

        if not sorted_posts:
            break  # No recent images

        images.extend(sorted_posts)
        
        # Check if the oldest post is older than 2 weeks
        oldest_post_date = int(sorted_posts[-1].get("change", 0))
        if oldest_post_date < filter_day_range:
            break

        page += 1

    return images

def process_series_data(rate_limited=True):
    """Fetch and process character data dynamically for each series.
    
    - Saves results in `output/` during normal runs.
    - Saves results in `test_output/` when running tests.
    """
    results = []

    for series in SERIES_LIST:
        print(f"DEBUG: Processing series: {series}")

        images = fetch_series_images(series, rate_limited)
        if not images:
            print(f"DEBUG: No images found for {series}. Skipping...")
            continue

        top_characters = extract_top_characters(images)
        if not top_characters:
            print(f"DEBUG: No characters found for {series}. Skipping...")
            continue

        for character in top_characters:
            char_images = fetch_character_images(character, rate_limited)
            if not char_images:
                print(f"DEBUG: No images found for {character}. Skipping...")
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

    # Determine output directory based on test mode
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    output_dir = "test_output" if TEST_MODE else "output"
    os.makedirs(output_dir, exist_ok=True)

    # Create filename with timestamp
    output_file = os.path.join(output_dir, f"{timestamp}_booru_gacha_results.json")

    # Ensure file is created
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)

    print(f"DEBUG: Results saved to {output_file}")
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch gacha character images from Booru.")
    parser.add_argument("--fast", action="store_true", help="Disable rate limiting for faster requests.")
    
    args = parser.parse_args()
    rate_limited = not args.fast  # Default is True (rate-limited mode)

    character_data = process_series_data(rate_limited)
    output_file = "booru_gacha_results.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(character_data, f, indent=4)