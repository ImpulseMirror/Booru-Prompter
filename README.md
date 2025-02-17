# Booru-Prompter

This Python application dynamically determines the **top 5 most popular characters** for each gacha series in the last two weeks, then fetches their image statistics.

## Features
- Dynamically finds the **top 5 most popular characters** for each series.
- Fetches images from the **last 14 days only**.
- Collects **character name, series name, number of images found, and aggregated tags**.
- Supports **rate-limited mode** (default) and **fast mode** (`--fast` flag).
- Saves results in a JSON file.

## API Documentation
This script uses the **Gelbooru API**:
- [Gelbooru API Docs](https://gelbooru.com/index.php?page=help&topic=dapi)

## Installation
1. Install Python (3.7+ recommended).
2. Install dependencies:
   ```sh
   pip install requests
   ```

## Usage

Run Normally (Rate-Limited)

By default, requests are limited to 1 per second:

```
python main.py
```

Run in Fast Mode (No Rate Limit)

If you want to disable the rate limit, use:

```
python main.py --fast
```

⚠️ Warning: This may hit API rate limits and cause errors.

Output

Results are saved in:

booru_gacha_results.json

Example JSON output:
```
[
    {
        "character_name": "Raiden Shogun",
        "series_name": "Genshin Impact",
        "num_images_found": 23,
        "aggregated_tags": ["thighhighs", "genshin_impact", "raiden_shogun", "cleavage", "solo"]
    }
]
```

# Notes

The Booru API used is Gelbooru, but this can be modified in config.py.

API rate limits may affect request speed.


This should now be perfectly formatted for GitHub! Let me know if you need any other adjustments. 🚀
