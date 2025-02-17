import json
import requests
import time
import argparse
from datetime import datetime, timedelta
from collections import Counter
from config import BOORU_API_URL, SERIES_LIST

# Get date range for the last two weeks
two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

def fetch_series_images(series_name, rate_limited=True):
    """Fetch all images for a given series from the last two weeks."""
    params = {
        "tags": f"{series_name} date:>{two_weeks_ago}",
        "limit": 200  # Fetch up to 200 images for better tag aggregation
    }
    
    response = requests.get(BOORU_API_URL, params=params)
    if rate_limited:
        time.sleep(1)  # Enforce rate limit (1 request per second)
    
    if response.status_code == 200:
        return response.json().get("post", [])
    return []

def extract_top_characters(images):
    """Extract the top 5 most common character tags from images."""
    tag_counter = Counter()
    
    for img in images:
        tags = img.get("tags", "").split()
        for tag in tags:
            if "character" in tag:  # Filtering character-related tags
                tag_counter[tag] += 1
    
    return [char[0] for char in tag_counter.most_common(5)]

def fetch_character_images(character_name, rate_limited=True):
    """Fetch images for a specific character."""
    params = {
        "tags": f"{character_name} date:>{two_weeks_ago}",
        "limit": 100
    }
    
    response = requests.get(BOORU_API_URL, params=params)
    if rate_limited:
        time.sleep(1)  # Enforce rate limit
    
    if response.status_code == 200:
        return response.json().get("post", [])
    return []

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
