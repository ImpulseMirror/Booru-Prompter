import json
import requests
import time
import argparse
import os
from datetime import datetime, timedelta
from collections import Counter
from config import BOORU_API_URL, TAG_API_URL, API_KEY, TOP_CHARACTER_LIMIT, USER_ID, SERIES_LIST, IMAGE_FILTER_DAYS
from tqdm import tqdm

# Global settings
TEST_MODE = False
TEST_OUTPUT_DIR = "test_output"
OUTPUT_DIR = "output"
TAG_DIR = "tags"
KNOWN_TAGS_FILE = os.path.join(TAG_DIR, "known_tags.json")
os.makedirs(TAG_DIR, exist_ok=True)

if not API_KEY or not USER_ID:
    raise ValueError("API_KEY and USER_ID must be set in config_secret.py")

filter_day_range = int((datetime.now() - timedelta(days=IMAGE_FILTER_DAYS)).timestamp())

def make_request(url, params, retries=3, rate_limited=True):
    """Make an API request with retries and optional rate limiting."""
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [403, 429]:
                time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
    return None

def load_json(filepath, default_data):
    """Load JSON data from a file or return default data."""
    if not os.path.exists(filepath):
        return default_data
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)

def save_json(filepath, data):
    """Save JSON data to a file."""
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def load_known_tags():
    """Load known character tags from a JSON file."""
    return load_json(KNOWN_TAGS_FILE, {"character_tags": [], "other_tags": [], "ignore_characters": []})

def save_known_tags(tags_data):
    """Save updated known character tags."""
    save_json(KNOWN_TAGS_FILE, tags_data)

def verify_character(tag):
    """Check if a tag represents a character."""
    tags_data = load_known_tags()
    if tag in tags_data["character_tags"]:
        return True
    if tag in tags_data["other_tags"]:
        return False

    response = make_request(TAG_API_URL, {"name": tag, "json": 1})
    if not response or "tag" not in response:
        tags_data["other_tags"].append(tag)
    else:
        for tag_info in response["tag"]:
            if tag_info["name"] == tag and tag_info.get("type") == 4:
                tags_data["character_tags"].append(tag)
                save_known_tags(tags_data)
                return True
    save_known_tags(tags_data)
    return False

def fetch_images(tag, rate_limited=True):
    """Fetch images for a given tag (series or character) from the booru API."""
    images, page = [], 0
    while True:
        params = {
            "tags": tag,
            "limit": 100,
            "pid": page,
            "json": 1,
            "api_key": API_KEY,
            "user_id": USER_ID
        }
        data = make_request(BOORU_API_URL, params, rate_limited=rate_limited)
        if not data or "post" not in data:
            break

        recent_posts = [img for img in data["post"] if int(img.get("change", 0)) > filter_day_range]
        if not recent_posts:
            break
        
        images.extend(recent_posts)
        page += 1
    return images

def extract_top_characters(images):
    """Extract and rank the most frequently appearing characters in images."""
    tag_counter = Counter(tag for image in images for tag in image.get("tags", "").split())
    valid_characters = {tag for tag in tag_counter if verify_character(tag)}
    return sorted(valid_characters, key=lambda t: tag_counter[t], reverse=True)[:TOP_CHARACTER_LIMIT]

def process_series(series_name):
    """Process image data for a specific series."""
    print(f"Processing series: {series_name}")
    images = fetch_images(series_name)
    if not images:
        print(f"No images found for {series_name}")
        return None
    
    top_characters = extract_top_characters(images)
    character_data = {}
    for character in tqdm(top_characters, desc=f"Processing {series_name}"):
        character_data[character] = analyze_character_images(character, images)
    return {
        "total_images_found": len(images),
        "characters": character_data
    }

def analyze_character_images(character, series_images):
    """Analyze and aggregate tags for a given character."""
    character_images = [img for img in series_images if character in img.get("tags", "").split()]
    tag_counter = Counter(tag for img in character_images for tag in img.get("tags", "").split())
    tag_counter.pop(character, None)
    return {
        "num_images_found": len(character_images),
        "aggregated_tags": dict(tag_counter.most_common())
    }

def process_all_series(rate_limited=True):
    """Fetch and process image data for all configured series."""
    series_results = {series: process_series(series) for series in SERIES_LIST}
    output_file = save_results(series_results)
    print(f"Results saved to {output_file}")

def save_results(results):
    """Save the final processed results to a JSON file."""
    output_folder = TEST_OUTPUT_DIR if TEST_MODE else OUTPUT_DIR
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    output_file = os.path.join(output_folder, f"{timestamp}_booru_gacha_results.json")
    save_json(output_file, {"series": results})
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch gacha character images from Booru.")
    parser.add_argument("--fast", action="store_true", help="Disable rate limiting for faster requests.")
    args = parser.parse_args()
    process_all_series(rate_limited=not args.fast)
