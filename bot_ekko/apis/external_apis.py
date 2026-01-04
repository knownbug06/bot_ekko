import requests
from concurrent.futures import ThreadPoolExecutor
from bot_ekko.core.logger import get_logger

logger = get_logger("ExternalAPIs")

class ExternalAPIs:
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.session = requests.Session()

    def _request(self, method, url, callback=None, **kwargs):
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

    def get(self, url, params=None, callback=None, **kwargs):
        self.executor.submit(self._request, 'GET', url, params=params, callback=callback, **kwargs)

    def post(self, url, data=None, json=None, callback=None, **kwargs):
        self.executor.submit(self._request, 'POST', url, data=data, json=json, callback=callback, **kwargs)
    
    def put(self, url, data=None, callback=None, **kwargs):
        self.executor.submit(self._request, 'PUT', url, data=data, callback=callback, **kwargs)

    def delete(self, url, callback=None, **kwargs):
        self.executor.submit(self._request, 'DELETE', url, callback=callback, **kwargs)

    def shutdown(self):
        self.executor.shutdown(wait=False)
