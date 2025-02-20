import json
import requests
import time
import argparse
import json
import os
from datetime import datetime, timedelta
from collections import Counter
from config import BOORU_API_URL, TAG_API_URL, API_KEY, TOP_CHARACTER_LIMIT, USER_ID, SERIES_LIST
from config import IMAGE_FILTER_DAYS

# Global flag to determine whether the script is running in test mode
TEST_MODE = False
TEST_OUTPUT_DIR = "test_output"
OUTPUT_DIR = "output"
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
    """Load known tags from the JSON file or create a new structure if missing."""
    if not os.path.exists(KNOWN_TAGS_FILE):
        return {"character_tags": [], "other_tags": [], "ignore_characters": []}

    with open(KNOWN_TAGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Ensure the ignore_characters property exists
    if "ignore_characters" not in data:
        data["ignore_characters"] = []

    return data

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
    """Fetch all images for a given series from the last X days, ensuring pagination works correctly."""
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

        # Dynamically compute cutoff time for recent posts
        current_time = datetime.now().timestamp()
        cutoff_time = int(current_time - (IMAGE_FILTER_DAYS * 24 * 60 * 60))  # Adjustable time range from config.py

        filtered_posts = [img for img in sorted_posts if int(img.get("change", 0)) > cutoff_time]

        print(f"DEBUG: Retrieved {len(sorted_posts)} images, {len(filtered_posts)} after filtering for {series_name}")

        if not filtered_posts:
            break  # Stop fetching older images

        images.extend(filtered_posts)
        page += 1  # Move to the next page

    return images

def normalize_tag(tag):
    return tag.lower().replace(" ", "_")

def extract_top_characters(images):
    """Identify the top characters from a set of images."""
    known_tags = load_known_tags()
    ignored_characters = set(known_tags["ignore_characters"])

    tag_counter = Counter()
    
    for image in images:
        tags = image.get("tags", "").split()
        tag_counter.update(tags)

    # Validate tags as actual character names
    valid_characters = {tag for tag in tag_counter if verify_character(tag)}

    # Exclude ignored characters BEFORE ranking
    valid_characters -= ignored_characters

    # Debugging: Print character candidates
    print(f"DEBUG: Valid characters before sorting: {valid_characters}")

    # Sort by frequency and select the top 5
    sorted_characters = sorted(valid_characters, key=lambda tag: tag_counter[tag], reverse=True)[:TOP_CHARACTER_LIMIT]

    print(f"DEBUG: Top characters selected: {sorted_characters}")

    return sorted_characters

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
    """Fetches data for each series, groups characters under their series, and aggregates tags with counts."""
    series_results = []
    known_tags = load_known_tags()
    ignored_characters = set(known_tags["ignore_characters"])

    for series_name in SERIES_LIST:
        print(f"DEBUG: Processing series: {series_name}")

        # Fetch images for this series
        images = fetch_series_images(series_name, rate_limited)
        total_images_found = len(images)  # Count total images retrieved for this series

        if not images:
            print(f"DEBUG: No images found for {series_name}")
            continue

        # Extract characters from the series, excluding ignored ones
        top_characters = extract_top_characters(images)
        filtered_characters = [char for char in top_characters if char not in ignored_characters]

        if not filtered_characters:
            print(f"DEBUG: No valid characters found for {series_name} after filtering ignored characters")
            continue

        character_data = {}
        for character in filtered_characters:
            # Count only images where this character appears
            character_images = [img for img in images if character in img.get("tags", "").split()]

            if not character_images:
                print(f"DEBUG: No images found for {character}")
                continue

            num_images_found = len(character_images)

            # Count all tags in relevant images
            tag_counter = Counter()
            for image in character_images:
                tags = image.get("tags", "").split()
                tag_counter.update(tags)

            # Remove character tags from the count
            tag_counter.pop(character, None)

            # Sort tags by occurrence
            sorted_tags = dict(sorted(tag_counter.items(), key=lambda x: x[1], reverse=True))

            # Store character data under `characters`
            character_data[character] = {
                "num_images_found": num_images_found,
                "aggregated_tags": sorted_tags
            }

        # Sort characters by number of images found (descending order)
        sorted_character_data = dict(
            sorted(character_data.items(), key=lambda x: x[1]["num_images_found"], reverse=True)
        )

        # Store series data with total images found and character data
        series_results.append({
            series_name: {
                "total_images_found": total_images_found,
                "characters": sorted_character_data
            }
        })

    # Generate timestamped output filename
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    output_folder = TEST_OUTPUT_DIR if TEST_MODE else OUTPUT_DIR
    os.makedirs(output_folder, exist_ok=True)
    output_file = os.path.join(output_folder, f"{timestamp}_booru_gacha_results.json")

    # Wrap results in "series" key and save as JSON
    final_output = {"series": series_results}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)

    print(f"Results saved to {output_file}")
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