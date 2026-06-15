import time
from enum import Enum, auto
from typing import List, Optional

import numpy as np

from bot_ekko.core.base import ThreadedService, ServiceStatus
from bot_ekko.core.errors import ServiceDependencyError
from bot_ekko.core.models import ServiceSttConfig, CommandNames
from bot_ekko.modules import audio_vis

# Seconds to ignore wake word after any trigger or transcription (kills echo re-triggers)
_WAKE_COOLDOWN_S = 4.0
# Consecutive above-threshold frames required before firing (rejects single-frame noise spikes)
_CONSECUTIVE_FRAMES = 2
# Seconds to spend measuring background noise right after the wake word fires.
# During this window audio is NOT recorded — we're building the noise floor estimate.
_CALIB_DURATION_S = 0.6
# Noise floor multiplier: speech threshold = noise_floor_rms × this value.
# Voice is typically 3-8× louder than ambient noise; 3.5 is a safe midpoint.
_NOISE_MULT = 3.5
# Hard floor/ceiling so the threshold stays sensible even in dead silence or very loud rooms.
_THRESHOLD_MIN = 0.01
_THRESHOLD_MAX = 0.20
# Seconds in RECORDING with no speech detected before giving up
_NO_SPEECH_TIMEOUT_S = 5.0


class _Stage(Enum):
    WAKE_WORD = auto()
    CALIBRATING = auto()   # measuring noise floor (~0.6 s)
    RECORDING = auto()     # VAD-gated capture
    TRANSCRIBING = auto()


class SttService(ThreadedService):
    """
    Full speech pipeline: wake word (openwakeword) → adaptive noise calibration
    → VAD capture → Whisper transcription.

    Noise floor is re-measured on every wake word trigger so the threshold
    adapts to fans, TVs, or any ambient background automatically.
    Mic must be configured at 16 000 Hz mono.
    """

    def __init__(self, service_stt_config: ServiceSttConfig, mic_service,
                 command_center=None, llm_service=None, name: str = "stt"):
        super().__init__(name, enabled=service_stt_config.enabled)
        self.cfg = service_stt_config
        self.mic_service = mic_service
        self.command_center = command_center
        self.llm_service = llm_service
        self.sample_rate: int = mic_service.sample_rate

        self._oww = None
        self._whisper = None

        self._stage = _Stage.WAKE_WORD
        self._speech_buffer: List[np.ndarray] = []
        self._silence_count = 0
        self._speech_started = False
        self._last_wake_time = 0.0
        self._wake_hit_count = 0

        # Calibration state
        self._calib_start_time = 0.0
        self._calib_rms_samples: List[float] = []
        self._speech_threshold = _THRESHOLD_MIN   # updated after calibration

        # No-speech timeout
        self._recording_start_time = 0.0

    def init(self) -> None:
        super().init()
        try:
            import openwakeword
            from openwakeword.model import Model as OWWModel
            self.logger.info("Ensuring openwakeword models are downloaded...")
            openwakeword.utils.download_models()
            self._oww = OWWModel(
                wakeword_models=[self.cfg.wake_word],
                inference_framework="onnx",
            )
            self.logger.info("Wake word model loaded: %s", self.cfg.wake_word)
        except Exception as e:
            raise ServiceDependencyError("Wake word model load failed", self.name) from e

        try:
            from faster_whisper import WhisperModel
            self._whisper = WhisperModel(
                self.cfg.model_size,
                device="cpu",
                compute_type="int8",
            )
            self.logger.info("Whisper model loaded: %s", self.cfg.model_size)
        except Exception as e:
            raise ServiceDependencyError("Whisper model load failed", self.name) from e

    # -- helpers ---------------------------------------------------------------

    def _to_int16(self, raw: bytes) -> np.ndarray:
        return np.frombuffer(raw, dtype=np.int16)

    def _to_float32(self, pcm16: np.ndarray) -> np.ndarray:
        return pcm16.astype(np.float32) / 32768.0

    def _rms(self, audio: np.ndarray) -> float:
        return float(np.sqrt(np.mean(audio ** 2)))

    def _set_state(self, state: str) -> None:
        """Transition to state and save current state to history for later restore."""
        if self.command_center:
            self.command_center.issue_command(
                CommandNames.CHANGE_STATE,
                params={"target_state": state, "save_history": True},
            )

    def _restore_state(self) -> None:
        """Restore the state that was saved when LISTENING began."""
        if self.command_center:
            self.command_center.issue_command(CommandNames.RESTORE_STATE)

    # -- wake word -------------------------------------------------------------

    def _check_wake_word(self, pcm16: np.ndarray) -> bool:
        # Don't interrupt while the LLM is composing/displaying a response.
        # Keep the cooldown anchor pushed forward the whole time so that when
        # the LLM finishes there's still a full _WAKE_COOLDOWN_S of quiet before
        # a new wake word can fire. Without this, ambient noise (TV/fan) would
        # immediately re-trigger LISTENING the instant the response disappears,
        # because the cooldown set at transcription time expired long ago.
        if self.llm_service and self.llm_service.is_busy:
            self._wake_hit_count = 0
            self._last_wake_time = time.time()
            return False
        if time.time() - self._last_wake_time < _WAKE_COOLDOWN_S:
            self._wake_hit_count = 0
            return False

        scores = self._oww.predict(pcm16)
        score = float(scores.get(self.cfg.wake_word, 0.0))

        if score >= self.cfg.wake_word_threshold:
            self._wake_hit_count += 1
            if self._wake_hit_count >= _CONSECUTIVE_FRAMES:
                self._wake_hit_count = 0
                self._last_wake_time = time.time()
                self.logger.info("Wake word confirmed (score=%.2f)", score)
                self.increment_stat("wake_word_triggers")
                return True
        else:
            self._wake_hit_count = 0

        return False

    # -- calibration -----------------------------------------------------------

    def _start_calibration(self) -> None:
        self._calib_start_time = time.time()
        self._calib_rms_samples = []
        self._stage = _Stage.CALIBRATING
        print("[STT] Calibrating noise floor...")

    def _calibrate_chunk(self, audio: np.ndarray) -> None:
        """Collect RMS samples for noise floor estimation."""
        self._calib_rms_samples.append(self._rms(audio))
        audio_vis.push_rms(self._rms(audio) * 4.0)

        if time.time() - self._calib_start_time >= _CALIB_DURATION_S:
            self._finish_calibration()

    def _finish_calibration(self) -> None:
        if self._calib_rms_samples:
            # Median is more robust than mean against the occasional loud transient
            noise_floor = float(np.median(self._calib_rms_samples))
            self._speech_threshold = float(np.clip(
                noise_floor * _NOISE_MULT,
                _THRESHOLD_MIN,
                _THRESHOLD_MAX,
            ))
        else:
            self._speech_threshold = _THRESHOLD_MIN

        self.logger.info(
            "Noise floor %.4f → speech threshold %.4f",
            float(np.median(self._calib_rms_samples)) if self._calib_rms_samples else 0,
            self._speech_threshold,
        )
        self.update_stat("speech_threshold", round(self._speech_threshold, 4))
        self._recording_start_time = time.time()
        self._stage = _Stage.RECORDING

    # -- recording -------------------------------------------------------------

    def _record_chunk(self, audio: np.ndarray) -> None:
        rms = self._rms(audio)
        audio_vis.push_rms(rms * 6.0)

        # Cancel if no speech at all within the timeout window
        if not self._speech_started:
            if time.time() - self._recording_start_time > _NO_SPEECH_TIMEOUT_S:
                self.logger.debug("No speech within %.1fs — cancelling", _NO_SPEECH_TIMEOUT_S)
                self._cancel_recording()
                return

        if rms > self._speech_threshold:
            self._speech_started = True
            self._silence_count = 0
            self._speech_buffer.append(audio)
        elif self._speech_started:
            self._silence_count += 1
            self._speech_buffer.append(audio)
            if self._silence_count >= self.cfg.silence_chunks_to_stop:
                self._stage = _Stage.TRANSCRIBING

    def _cancel_recording(self) -> None:
        self._speech_buffer.clear()
        self._silence_count = 0
        self._speech_started = False
        self._last_wake_time = time.time()
        audio_vis.clear()
        self._restore_state()
        self._stage = _Stage.WAKE_WORD
        wake_label = self.cfg.wake_word.replace("_", " ")
        print(f"[STT] Listening for '{wake_label}'...")

    # -- transcription ---------------------------------------------------------

    def _transcribe_and_reset(self) -> None:
        transcript = None

        if len(self._speech_buffer) < self.cfg.min_speech_chunks:
            self.logger.debug("Utterance too short (%d chunks) — discarded", len(self._speech_buffer))
        else:
            audio = np.concatenate(self._speech_buffer)
            try:
                segments, _ = self._whisper.transcribe(audio, language="en", beam_size=5)
                text = " ".join(seg.text for seg in segments).strip()
                if text:
                    print(f"[STT] {text}")
                    self.logger.info("Transcript: %s", text)
                    self.update_stat("last_transcript", text)
                    self.increment_stat("transcriptions")
                    transcript = text
                else:
                    self.logger.debug("Transcription returned empty string")
            except Exception as e:
                self.logger.error("Transcription failed: %s", e)
                self.update_stat("last_error", str(e))

        self._speech_buffer.clear()
        self._silence_count = 0
        self._speech_started = False
        self._last_wake_time = time.time()
        audio_vis.clear()
        self._stage = _Stage.WAKE_WORD
        wake_label = self.cfg.wake_word.replace("_", " ")
        print(f"[STT] Listening for '{wake_label}'...")

        if transcript and self.llm_service:
            # LlmService owns DISPLAY_TEXT and will issue RESTORE_STATE when done.
            # The pre-LISTENING state was saved to history by _set_state("LISTENING").
            self.llm_service.handle_transcript(transcript)
        else:
            # No LLM — restore to pre-LISTENING state ourselves.
            self._restore_state()

    # -- main loop -------------------------------------------------------------

    def _run(self) -> None:
        wake_label = self.cfg.wake_word.replace("_", " ")

        self.logger.info("Waiting for MicService to be ready...")
        while not self._stop_event.is_set() and self.mic_service.status != ServiceStatus.RUNNING:
            time.sleep(0.5)
        if self._stop_event.is_set():
            return

        print(f"[STT] Ready — say '{wake_label}' to start speaking.")

        while not self._stop_event.is_set():
            chunks = self.mic_service.read_mic()
            if not chunks:
                time.sleep(0.01)
                continue

            for raw in chunks:
                pcm16 = self._to_int16(raw)
                audio = self._to_float32(pcm16)

                if self._stage == _Stage.WAKE_WORD:
                    if self._check_wake_word(pcm16):
                        print("[STT] Wake word detected — calibrating...")
                        audio_vis.clear()
                        self._set_state("LISTENING")
                        self._start_calibration()

                elif self._stage == _Stage.CALIBRATING:
                    self._calibrate_chunk(audio)

                elif self._stage == _Stage.RECORDING:
                    self._record_chunk(audio)

                if self._stage == _Stage.TRANSCRIBING:
                    self._transcribe_and_reset()

    def stop(self) -> None:
        super().stop()

    def update(self) -> None:
        pass
