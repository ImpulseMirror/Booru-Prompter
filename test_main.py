import unittest
import json
import os
from unittest.mock import patch
from main import fetch_series_images, extract_top_characters, fetch_character_images, verify_character, process_series_data
from unittest.mock import patch
from datetime import datetime, timedelta

# Sample mock data for API responses
MOCK_IMAGE_DATA = [
    {
        "change": "1700000000",  # Recent timestamp
        "tags": "raiden_shogun genshin_impact character female purple_hair"
    },
    {
        "change": "1690000000",  # Old timestamp (older than 2 weeks)
        "tags": "hutao genshin_impact character orange_eyes"
    },
    {
        "change": "1700001000", 
        "tags": "hutao genshin_impact character chibi cute"
    }
]

MOCK_TAG_DATA = [
    {"name": "raiden_shogun", "type": 4},
    {"name": "hutao", "type": 4},
    {"name": "not_a_character", "type": 1}
]

class TestBooruGachaFetcher(unittest.TestCase):

    @patch("main.datetime")
    @patch("main.make_request")
    def test_fetch_series_images(self, mock_request, mock_datetime):
        """Test that fetch_series_images correctly retrieves and filters recent images dynamically."""
        override_time = 1700000500
        # Mock the current time to be just before our newest test data (so it's always within 2 weeks)
        mock_now = datetime.fromtimestamp(override_time)  # Future date close to test data
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)  # Keep normal datetime behavior

        # Mock API response with test image data
        mock_request.return_value = {"post": MOCK_IMAGE_DATA}

        # Run function under test
        images = fetch_series_images("Genshin Impact", rate_limited=False)

        # Ensure images are retrieved
        self.assertGreater(len(images), 0, "Should return at least one recent image")

        # Ensure all images are 'recent' dynamically
        self.assertTrue(all(int(img["change"]) > (override_time - (14 * 24 * 60 * 60)) for img in images), 
                        "All images should be within the last 2 weeks")

    @patch("main.make_request")
    def test_extract_top_characters(self, mock_request):
        """Test that extract_top_characters correctly identifies and filters character tags."""
        mock_request.return_value = MOCK_TAG_DATA
        characters = extract_top_characters(MOCK_IMAGE_DATA)

        self.assertIn("raiden_shogun", characters, "Raiden Shogun should be a top character")
        self.assertIn("hutao", characters, "Hutao should be a top character")
        self.assertNotIn("not_a_character", characters, "Non-character tags should be filtered out")

    @patch("main.make_request")
    def test_fetch_character_images(self, mock_request):
        """Test that fetch_character_images fetches images correctly for a valid character."""
        mock_request.return_value = {"post": MOCK_IMAGE_DATA}
        images = fetch_character_images("raiden_shogun", rate_limited=False)

        self.assertGreater(len(images), 0, "Should return images for a valid character")

    @patch("main.make_request")
    def test_verify_character(self, mock_request):
        """Test that verify_character correctly confirms valid character tags."""
        mock_request.return_value = MOCK_TAG_DATA
        self.assertTrue(verify_character("raiden_shogun"), "Raiden Shogun should be verified as a character")
        self.assertFalse(verify_character("not_a_character"), "Invalid characters should be filtered out")

    @patch("main.fetch_series_images")
    @patch("main.fetch_character_images")
    @patch("main.extract_top_characters")
    def test_process_series_data(self, mock_extract_top_characters, mock_fetch_character_images, mock_fetch_series_images):
        """Test that process_series_data runs without errors and returns valid results."""

        # Mock fetch_series_images() to return image data
        mock_fetch_series_images.return_value = MOCK_IMAGE_DATA

        # Mock extract_top_characters() to return character names
        mock_extract_top_characters.return_value = ["raiden_shogun", "hutao"]

        # Mock fetch_character_images() to return images for characters
        mock_fetch_character_images.return_value = MOCK_IMAGE_DATA  

        # Run function under test
        data = process_series_data(rate_limited=False)
        
        # Ensure at least one character is returned
        self.assertGreater(len(data), 0, "Process should return at least one character entry")

    @patch("main.make_request")
    def test_fetch_series_images_no_results(self, mock_request):
        """Test that fetch_series_images correctly returns an empty list when no results are found."""
        mock_request.return_value = {"post": []}  # API returns no posts

        images = fetch_series_images("Genshin Impact", rate_limited=False)

        self.assertEqual(images, [], "fetch_series_images should return an empty list when no images are found")

    @patch("main.make_request")
    def test_fetch_character_images_no_results(self, mock_request):
        """Test that fetch_character_images returns an empty list when no character images are found."""
        mock_request.return_value = {"post": []}  # API returns no images

        images = fetch_character_images("raiden_shogun", rate_limited=False)

        self.assertEqual(images, [], "fetch_character_images should return an empty list when no images are found")

    @patch("main.fetch_series_images", return_value=[])
    @patch("main.fetch_character_images", return_value=[])
    @patch("main.extract_top_characters", return_value=[])
    def test_process_series_data_no_results(self, mock_extract_top_characters, mock_fetch_character_images, mock_fetch_series_images):
        """Test that process_series_data still generates a valid empty file when no results are found."""
        
        # Run function in test mode
        output_file = process_series_data(rate_limited=False, test_mode=True)

        # Ensure the output file was created
        self.assertTrue(os.path.exists(output_file), "Results file should still be generated")

        # Ensure file contains an empty list
        with open(output_file, "r") as f:
            file_content = json.load(f)
            self.assertEqual(file_content, [], "File should contain an empty list when no data is found")

if __name__ == "__main__":
    unittest.main()