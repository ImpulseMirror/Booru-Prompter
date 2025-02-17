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
    "Taimanin",
    "Blue Archive",
    "Genshin Impact",
    "Honkai Star Rail",
    "Fate Grand Order",
    "Nikke"
]