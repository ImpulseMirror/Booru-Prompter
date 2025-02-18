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

## Running Unit Tests

To verify the functionality of this project, you can run the **unit tests** which simulate API responses.

### **1. Install Testing Dependencies**
Make sure you have **`unittest`** installed (it comes with Python by default).

If you haven't already installed the project dependencies, install them with:
```sh
pip install requests
```

### **2. Run Tests

Run all unit tests with:

```sh
python -m unittest discover
```

or 

```sh
python test_main.py
```

### **3. What Do the Tests Cover?

✅ API Request Handling - Ensures images are fetched correctly and old images are filtered.
✅ Character Extraction - Confirms that only actual character tags are counted.
✅ Rate Limit & Error Handling - Simulates API limits and retries.
✅ Data Processing - Verifies that the final output format is correct.

If a test fails, you’ll see an error message. If all tests pass, you’ll see:

```sh
----------------------------------------------------------------------
Ran 5 tests in 0.XXXs

OK
```

