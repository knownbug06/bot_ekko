import os
import json
import random
import requests
from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import CommandNames
from bot_ekko.apis.external_apis import ExternalAPIs

logger = get_logger("GifAPI")

class GifAPI:
    def __init__(self, command_center, api_key: str):
        self.command_center = command_center
        self.api_key = api_key
        self.external_apis = ExternalAPIs()
        self.temp_dir = os.path.join(os.getcwd(), "bot_ekko", "assets", "temp_gifs")
        os.makedirs(self.temp_dir, exist_ok=True)

    def fetch_random_gif(self, query: str):
        url = "https://api.giphy.com/v1/gifs/random"
        params = {
            "api_key": self.api_key,
            "tag": query,
            "rating": "g"
        }
        logger.info(f"Fetching random gif for: {query}")
        self.external_apis.get(url, params=params, callback=self._on_gif_received)

    def _on_gif_received(self, response):
        if not response or response.status_code != 200:
            logger.error("Failed to fetch GIF metadata")
            return

        try:
            data = response.json()
            # Giphy random endpoint structure: data.data.images.original.url
            gif_url = data.get('data', {}).get('images', {}).get('original', {}).get('url')
            
            if not gif_url:
                logger.error("No GIF URL found in response")
                return

            self._download_gif(gif_url)
        except Exception as e:
            logger.error(f"Error parsing GIF response: {e}")

    def _download_gif(self, url):
        try:
            # Download the actual GIF content
            # We use a separate request here. Since it's inside a callback running in a thread from ExternalAPIs,
            # we are already in a background thread. We can just use requests directly or reuse external_apis synchronously?
            # Reusing external_apis would spawn another thread. Let's just use requests directly since we are already off-main-thread.
            response = requests.get(url) 
            if response.status_code == 200:
                filename = f"temp_{random.randint(0, 1000)}.gif"
                filepath = os.path.join(self.temp_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Downloaded GIF to {filepath}")
                self._trigger_display(filepath)
            else:
                logger.error(f"Failed to download GIF content: {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading GIF: {e}")

    def _trigger_display(self, filepath):
        # We need to ensure we're passing what state_renderer expects.
        # Assuming CANVAS state can handle 'image_path' or similar. 
        # I'll check state_renderer.py in the next step to confirm param name, but for now I'll use 'media_path' 
        # based on common convention, and I will verify/fix it.
        params = {
            "target_state": "CANVAS",
            "media_type": "gif",
            "media_path": filepath
        }
        self.command_center.issue_command(CommandNames.CHANGE_STATE, params=params)

    def stop(self):
        self.external_apis.shutdown()
