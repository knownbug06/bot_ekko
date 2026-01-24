import os
import random
import requests
from typing import Optional, Any
from requests import Response

from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import CommandNames
from bot_ekko.apis.external_apis import ExternalAPIs

logger = get_logger("TenorAPI")

class TenorAPI:
    """
    Adapter for interacting with the Tenor GIF API.
    Fetches and downloads GIFs locally for playback.
    """
    def __init__(self, command_center: Any, api_key: str, client_key: str = "bot_ekko") -> None:
        """
        Initialize the Tenor API Adapter.

        Args:
            command_center (CommandCenter): Command issuer.
            api_key (str): Tenor API Key.
            client_key (str, optional): Client ID. Defaults to "bot_ekko".
        """
        self.command_center = command_center
        self.api_key = api_key
        self.client_key = client_key
        self.external_apis = ExternalAPIs()
        self.temp_dir = os.path.join(os.getcwd(), "bot_ekko", "assets", "temp_gifs")
        os.makedirs(self.temp_dir, exist_ok=True)

    def fetch_random_gif(self, query: str, limit: int = 1) -> None:
        """
        Fetches a random GIF for the given query.

        Args:
            query (str): Search term.
            limit (int, optional): Number of results to fetch to pick from. Defaults to 1.
        """
        # Tenor V2 Endpoint
        url = "https://tenor.googleapis.com/v2/search"
        params = {
            "q": query,
            "key": self.api_key,
            "client_key": self.client_key,
            "limit": limit,
            "media_filter": "gif" 
        }
        logger.info(f"Fetching Tenor gif for: {query}")
        self.external_apis.get(url, params=params, callback=self._on_gif_received)

    def _on_gif_received(self, response: Optional[Response]) -> None:
        """Callback for when GIF metadata is received."""
        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch Tenor metadata: {response.status_code if response else 'No Response'}")
            return

        try:
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                logger.warning("No GIFs found for query.")
                return

            # Pick a random one from the limit we fetched (even if limit=1, logic holds)
            gif_entry = random.choice(results)
            
            # Tenor V2 structure: results[0].media_formats.gif.url
            media_formats = gif_entry.get("media_formats", {})
            gif_url = media_formats.get("gif", {}).get("url")
            
            if not gif_url:
                logger.error("No GIF URL found in media formats")
                return

            self._download_gif(gif_url)
        except Exception as e:
            logger.error(f"Error parsing Tenor response: {e}")

    def _download_gif(self, url: str) -> None:
        """Downloads the GIF from the URL."""
        try:
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

    def _trigger_display(self, filepath: str) -> None:
        """Issues a command to display the downloaded GIF."""
        params = {
            "target_state": "CANVAS",
            "media_type": "gif",
            "media_path": filepath,
            "save_history": True
        }
        self.command_center.issue_command(CommandNames.CHANGE_STATE, params=params)

    def stop(self) -> None:
        """Stops the underlying API client."""
        self.external_apis.shutdown()

