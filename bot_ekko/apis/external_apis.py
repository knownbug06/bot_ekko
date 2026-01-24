import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable, Any, Dict
from requests import Response

from bot_ekko.core.logger import get_logger

logger = get_logger("ExternalAPIs")

class ExternalAPIs:
    """
    Manages external API requests using a thread pool for non-blocking operations.
    """
    def __init__(self, max_workers: int = 5) -> None:
        """
        Initialize ExternalAPIs.

        Args:
            max_workers (int, optional): Max concurrent threads. Defaults to 5.
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.session = requests.Session()

    def _request(self, method: str, url: str, callback: Optional[Callable[[Optional[Response]], None]] = None, **kwargs: Any) -> Optional[Response]:
        """
        Internal request handler.
        
        Args:
            method (str): HTTP method.
            url (str): URL.
            callback (Callable, optional): Callback with Response object.
            **kwargs: Arguments for requests.request.
            
        Returns:
            Optional[Response]: The response object if successful, else None.
        """
        try:
            response = self.session.request(method, url, **kwargs)
            # You might want to raise_for_status() here or handle it in callback
            # response.raise_for_status() 
            if callback:
                callback(response)
            return response
        except Exception as e:
            logger.error(f"Request failed: {url} | Error: {e}")
            if callback:
                # Decide how you want to handle errors in callback.
                # Passing None or a custom error object are options.
                callback(None)
            return None

    def get(self, url: str, params: Optional[Dict] = None, callback: Optional[Callable[[Optional[Response]], None]] = None, **kwargs: Any) -> None:
        """Type-hinted wrapper for GET."""
        self.executor.submit(self._request, 'GET', url, params=params, callback=callback, **kwargs)

    def post(self, url: str, data: Any = None, json: Any = None, callback: Optional[Callable[[Optional[Response]], None]] = None, **kwargs: Any) -> None:
        """Type-hinted wrapper for POST."""
        self.executor.submit(self._request, 'POST', url, data=data, json=json, callback=callback, **kwargs)
    
    def put(self, url: str, data: Any = None, callback: Optional[Callable[[Optional[Response]], None]] = None, **kwargs: Any) -> None:
        """Type-hinted wrapper for PUT."""
        self.executor.submit(self._request, 'PUT', url, data=data, callback=callback, **kwargs)

    def delete(self, url: str, callback: Optional[Callable[[Optional[Response]], None]] = None, **kwargs: Any) -> None:
        """Type-hinted wrapper for DELETE."""
        self.executor.submit(self._request, 'DELETE', url, callback=callback, **kwargs)

    def shutdown(self) -> None:
        """Shuts down the executor."""
        self.executor.shutdown(wait=False)

