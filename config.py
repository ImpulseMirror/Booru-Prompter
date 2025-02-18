import os

# Booru API endpoints
BOORU_API_URL = "https://gelbooru.com/index.php?page=dapi&s=post&q=index"
TAG_API_URL = "https://gelbooru.com/index.php?page=dapi&s=tag&q=index"

# Load API credentials securely
try:
    from config_secret import API_KEY, USER_ID
except ImportError:
    print("Error: Missing config_secret.py. Create the file and add API_KEY and USER_ID.")
    API_KEY = None
    USER_ID = None

# List of gacha series to analyze
SERIES_LIST = [
    "taimanin_(series)",
    "blue_archive",
    "genshin_impact",
    "honkai_(series)",
    "honkai:_star_rail"
    "honkai_impact_3rd"
    "fate_(series)",
    "fate/grand_order",
    "nikke_(series)"
]

# Number of days to filter images from the API
IMAGE_FILTER_DAYS = 1  # Can be adjusted as needed