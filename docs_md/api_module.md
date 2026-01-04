# API Module Documentation

## Overview
The API Module provides a robust, non-blocking way for **Bot Ekko** to interact with external services (APIs). Since the robot runs on a strict 60FPS main loop, any blocking network calls would freeze the animations and responsiveness. This module solves that by offloading requests to background threads.

## Architecture

### 1. `ExternalAPIs` Core
**Path:** `bot_ekko/apis/external_apis.py`

This is the low-level wrapper around the `requests` library.
- **Threading**: Uses `concurrent.futures.ThreadPoolExecutor` to run requests in the background.
- **Session Management**: Maintains a `requests.Session` for connection pooling.
- **Methods**: Supports `get`, `post`, `put`, `delete`.
- **Callbacks**: Accepts a `callback` function that is executed when the request completes (note: the callback runs in the background thread, so be careful with thread safety when touching shared state).

**Usage Example:**
```python
from bot_ekko.apis.external_apis import ExternalAPIs

def my_callback(response):
    if response and response.status_code == 200:
        print(response.json())

api = ExternalAPIs()
api.get("https://api.example.com/data", callback=my_callback)
```

### 2. Adapters
**Path:** `bot_ekko/apis/adapters/`

Adapters are higher-level classes that use `ExternalAPIs` to perform specific tasks. They abstract the API details (endpoints, keys, parsing) away from the main bot logic.

#### Giphy Adapter (`GifAPI`)
**Path:** `bot_ekko/apis/adapters/gif_api.py`

- **Purpose**: Fetches random GIFs based on a search term and displays them on the robot's screen.
- **Integration**:
    1.  Fetches GIF metadata from Giphy API.
    2.  Downloads the GIF file to a temporary directory.
    3.  Issues a `CHANGE_STATE` command to the `CommandCenter` to switch the robot to `CANVAS` mode and play the GIF.
    4.  Requests `save_history=True` so the robot returns to its previous state (e.g., `ACTIVE`) after the GIF finishes.

**Instantiation:**
```python
# main.py
gif_api = GifAPI(command_center, API_KEY)
```

**Triggering:**
Can be triggered via Bluetooth command or code:
```python
# Bluetooth: "GIF;happy"
gif_api.fetch_random_gif("happy")
```

## Adding New APIs
To add a new API integration:
1.  Create a new file in `bot_ekko/apis/adapters/` (e.g., `weather_api.py`).
2.  Import `ExternalAPIs`.
3.  Implement your methods to call `external_apis.get/post`.
4.  In the callback, convert the response data into a `Command` (e.g., `CHANGE_STATE`, `SHOW_TEXT`) and issue it via `CommandCenter`.
