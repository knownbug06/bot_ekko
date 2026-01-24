import logging
import json
from typing import Optional, Callable, Any, Dict
from requests import Response

from bot_ekko.core.logger import get_logger
from bot_ekko.apis.external_apis import ExternalAPIs

logger = get_logger("ChatAPI")

class ChatAPI:
    """
    Adapter for interacting with the external Chat/LLM API.
    Manages session creation and message exchange.
    """
    def __init__(self, command_center: Any, url: str) -> None:
        """
        Initialize the Chat API Adapter.

        Args:
            command_center: Reference to command center (unused in this class but kept for consistency).
            url (str): Base URL of the Chat API.
        """
        self.command_center = command_center
        self.base_url = url
        self.external_apis = ExternalAPIs()
        self.session_id: Optional[str] = None
        self.pending_query: Optional[str] = None
        self.pending_callback: Optional[Callable[[str, bool], None]] = None

    def query(self, text: str, callback: Optional[Callable[[str, bool], None]] = None) -> None:
        """
        Send a chat query to the API.
        
        Args:
            text (str): The user's message.
            callback (Callable, optional): Function to call with response (text, is_error).
        """
        logger.info(f"Chat API Request: {text}")
        
        if self.session_id:
            self._send_chat_message(text, callback)
        else:
            logger.info("No session ID found. starting new session...")
            self.pending_query = text
            self.pending_callback = callback
            self._start_session()

    def _start_session(self) -> None:
        """Starts a new chat session."""
        url = f"{self.base_url}/v1/sessions"
        # POST /v1/sessions
        self.external_apis.post(url, json={}, callback=self._on_session_started)

    def _on_session_started(self, response: Optional[Response]) -> None:
        """Callback when session start request completes."""
        if not response or response.status_code != 200:
            logger.error(f"Failed to start session: {response.status_code if response else 'No Response'}")
            if self.pending_callback: 
                self.pending_callback("I couldn't connect to the server.", True)
            self.pending_query = None
            self.pending_callback = None
            return

        try:
            data = response.json()
            self.session_id = data.get("session_id")
            logger.info(f"Session started: {self.session_id}")
            
            if self.pending_query:
                # Need to use local vars as pending_callback needs to be passed
                cb = self.pending_callback
                self._send_chat_message(self.pending_query, cb)
                self.pending_query = None
                self.pending_callback = None
        except Exception as e:
            logger.error(f"Error parsing session response: {e}")
            if self.pending_callback:
                self.pending_callback("Error starting session.", True)

    def _send_chat_message(self, text: str, callback: Optional[Callable[[str, bool], None]]) -> None:
        """Sends a message to an active session."""
        if not self.session_id:
            logger.error("Attempted to chat without session ID")
            return

        url = f"{self.base_url}/v1/sessions/{self.session_id}/chat"
        payload = {"message": text}
        
        self.external_apis.post(url, json=payload, callback=self._create_chat_callback(callback))

    def _create_chat_callback(self, user_callback: Optional[Callable[[str, bool], None]]) -> Callable[[Optional[Response]], None]:
        """Creates a closure for handling the chat response."""
        def _internal_callback(response: Optional[Response]) -> None:
            if not response:
                logger.error("Chat API Request Failed: No Response")
                if user_callback: user_callback("I couldn't reach the server.", True)
                return

            if response.status_code != 200:
                logger.error(f"Chat API Request Failed: Status {response.status_code}")
                # Maybe session expired? We could retry, but for now just fail.
                if user_callback: user_callback("I encountered an error.", True)
                return
             
            try:
                data = response.json()
                # Expecting {"reply": "..."}
                text = data.get("reply")
                
                if not text:
                    logger.warning(f"No reply found in API response: {data}")
                    text = "I received an empty response."
                 
                if user_callback:
                    user_callback(text, False)
            except Exception as e:
                logger.error(f"Error parsing Chat API response: {e}")
                if user_callback: user_callback("I couldn't understand the response.", True)

        return _internal_callback

    def stop(self) -> None:
        """Stops the underlying API client."""
        self.external_apis.shutdown()

