import json
import os
import queue
import time

import httpx

from bot_ekko.core.base import ThreadedService
from bot_ekko.core.errors import ServiceDependencyError
from bot_ekko.core.models import ServiceLlmConfig, CommandNames
from bot_ekko.core.logger import get_logger
from bot_ekko.modules import llm_state
from bot_ekko.utils import is_connected

logger = get_logger("LlmService")


class LlmService(ThreadedService):
    """
    Receives transcripts from SttService, queries a local Ollama model,
    and streams the response into llm_state for the DISPLAY_TEXT renderer.

    Flow:
        handle_transcript(text)
            → DISPLAY_TEXT state (loading dots until first token)
            → stream tokens into llm_state
            → mark done → sleep → RESTORE_STATE
    """

    def __init__(self, service_llm_config: ServiceLlmConfig,
                 command_center=None, name: str = "llm"):
        super().__init__(name, enabled=service_llm_config.enabled)
        self.cfg = service_llm_config
        self.command_center = command_center
        self._queue: queue.Queue = queue.Queue()
        self._system_prompt: str = ""
        self.is_busy: bool = False

    def init(self) -> None:
        super().init()
        try:
            self._system_prompt = self._load_system_prompt()
            self.logger.info("System prompt loaded from %s", self.cfg.system_prompt_path)
        except Exception as e:
            raise ServiceDependencyError("System prompt load failed", self.name) from e

        # Verify Ollama is reachable (it's local, no internet needed)
        try:
            resp = httpx.get(f"{self.cfg.ollama_url}/api/tags", timeout=3.0)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            self.logger.info("Ollama reachable. Available models: %s", models)
            if self.cfg.model not in models:
                self.logger.warning("Configured model '%s' not found in Ollama", self.cfg.model)
        except Exception as e:
            raise ServiceDependencyError(f"Ollama not reachable at {self.cfg.ollama_url}", self.name) from e

    def _load_system_prompt(self) -> str:
        path = self.cfg.system_prompt_path
        if not os.path.isabs(path):
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base, path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    # -- public API called by SttService ---------------------------------------

    def handle_transcript(self, text: str) -> None:
        """Non-blocking: queues the transcript for processing in the service thread."""
        self._queue.put(text.strip())
        self.logger.info("Transcript queued: %s", text[:80])

    # -- internal processing ---------------------------------------------------

    def _set_state(self, state: str, params: dict = None) -> None:
        """Change state WITHOUT saving history — the pre-LISTENING save already happened in SttService."""
        if self.command_center:
            p = {"target_state": state}
            if params:
                p.update(params)
            self.command_center.issue_command(CommandNames.CHANGE_STATE, params=p)

    def _restore_prev_state(self) -> None:
        """Pop the pre-LISTENING state that SttService pushed when wake word fired."""
        if self.command_center:
            self.command_center.issue_command(CommandNames.RESTORE_STATE)

    def _process(self, user_text: str) -> None:
        self.is_busy = True
        self.logger.info("Processing: %s", user_text)
        self.increment_stat("requests")

        # Switch face to DISPLAY_TEXT (handler shows loading dots until first token)
        llm_state.start_stream()
        self._set_state("DISPLAY_TEXT")

        try:
            self._stream_ollama(user_text)
        except Exception as e:
            self.logger.error("Ollama error: %s", e)
            llm_state.mark_error(str(e))
            self.update_stat("last_error", str(e))

        llm_state.mark_done()
        self.logger.info("Response complete (%d chars)", len(llm_state.get_state()["text"]))
        self.update_stat("last_response_preview", llm_state.get_state()["text"][:100])

        # Let user read the response, then restore to the state that was active
        # before the wake word triggered (SLEEPING, ACTIVE, etc.)
        time.sleep(self.cfg.response_display_seconds)
        self._restore_prev_state()
        llm_state.reset()
        # Small buffer so the main loop processes RESTORE_STATE before we allow
        # the next wake word trigger — prevents SttService from immediately
        # re-entering LISTENING while the restore is still in the command queue.
        time.sleep(0.3)
        self.is_busy = False

    def _stream_ollama(self, user_text: str) -> None:
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user",   "content": user_text},
            ],
            "stream": True,
        }

        with httpx.Client(timeout=self.cfg.request_timeout) as client:
            with client.stream(
                "POST",
                f"{self.cfg.ollama_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        llm_state.append_token(token)
                    if data.get("done"):
                        break

    # -- service loop ----------------------------------------------------------

    def _run(self) -> None:
        self.logger.info("LLM service ready (model: %s)", self.cfg.model)
        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.2)
                self._process(text)
            except queue.Empty:
                continue

    def stop(self) -> None:
        super().stop()

    def update(self) -> None:
        pass
