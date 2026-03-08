import pyaudio
import sys
import queue
import wave
import os
import time
from typing import Optional, List

from bot_ekko.core.base import ThreadedService
from bot_ekko.core.errors import ServiceDependencyError
from bot_ekko.core.models import ServiceMicConfig


class MicService(ThreadedService):
    """
    Manages USB Microphone audio stream collection.
    Captures audio and places it in a thread-safe queue buffer.
    """
    def __init__(self, service_mic_config: ServiceMicConfig, name: str = "mic"):
        """
        Initialize the Mic Service.

        Args:
            service_mic_config (ServiceMicConfig): Configuration object.
            name (str, optional): Service name. Defaults to "mic".
        """
        super().__init__(name, enabled=service_mic_config.enabled)
        self.service_mic_config: ServiceMicConfig = service_mic_config
        self.audio_interface: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.chunk_size = self.service_mic_config.chunk_size
        self.sample_rate = self.service_mic_config.sample_rate
        self.channels = self.service_mic_config.channels
        self.audio_buffer: queue.Queue = queue.Queue(maxsize=self.service_mic_config.buffer_size)
        self.wav_file: Optional[wave.Wave_write] = None

    def init(self) -> None:
        """
        Initialize the Microphone service resources (pyaudio).
        
        Raises:
            ServiceDependencyError: If pyaudio fails to instantiate or stream cannot open.
        """
        super().init()
        try:
            self.audio_interface = pyaudio.PyAudio()
            self.stream = self.audio_interface.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            self.logger.info("Mic Service Initialized and stream opened successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Mic Service: {e}")
            if self.audio_interface:
                 self.audio_interface.terminate()
            raise ServiceDependencyError("Microphone initialization failed", self.name) from e

    def read_mic(self) -> Optional[List[bytes]]:
        """
        Reads all currently available audio chunks from the buffer.
        
        Returns:
            Optional[List[bytes]]: A list of raw byte chunks collected since the last read, or None if empty.
        """
        chunks = []
        try:
            while not self.audio_buffer.empty():
                chunks.append(self.audio_buffer.get_nowait())
        except queue.Empty:
            pass
            
        if not chunks:
            return None
        return chunks

    def _setup_audio_recording(self) -> None:
        """Sets up the wave file for recording if configured."""
        if self.service_mic_config.save_audio and self.service_mic_config.save_audio_path:
            try:
                os.makedirs(self.service_mic_config.save_audio_path, exist_ok=True)
                filename = f"recording_{int(time.time())}.wav"
                filepath = os.path.join(self.service_mic_config.save_audio_path, filename)
                self.wav_file = wave.open(filepath, 'wb')
                self.wav_file.setnchannels(self.channels)
                self.wav_file.setsampwidth(self.audio_interface.get_sample_size(pyaudio.paInt16))
                self.wav_file.setframerate(self.sample_rate)
                self.logger.info(f"Saving audio stream to: {filepath}")
            except Exception as e:
                self.logger.error(f"Failed to open wave file for writing: {e}")

    def _run(self) -> None:
        """
        Main service loop. Continuously reads from the audio stream and adds frames to the buffer.
        """
        self.logger.info("Starting Microphone Stream Collection.")
        
        self._setup_audio_recording()
        
        if not self.stream or not self.audio_interface:
             self.logger.error("Microphone stream not initialized")
             return

        try:
            while not self._stop_event.is_set():
                try:
                    # Read single chunk, non-blocking exceptions
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    if not self.audio_buffer.full():
                        self.audio_buffer.put_nowait(data)
                    else:
                        # Drop oldest chunk to make room
                        try:
                            self.audio_buffer.get_nowait()
                            self.audio_buffer.put_nowait(data)
                        except queue.Empty:
                            pass
                            
                    if self.wav_file:
                        self.wav_file.writeframes(data)
                        
                    self.increment_stat("chunks_collected")
                except Exception as e:
                     self.logger.error(f"Error reading stream chunk: {e}")
                     self.update_stat("last_error", str(e))
        except Exception as e:
            self.logger.error(f"Mic Service crashed: {e}")
            self.update_stat("crash_error", str(e))
            raise
        finally:
             self._cleanup()

    def _cleanup(self) -> None:
        """Clean up audio streams"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio_interface:
            self.audio_interface.terminate()
        if self.wav_file:
            try:
                self.wav_file.close()
            except Exception as e:
                self.logger.error(f"Error closing wave file: {e}")
        self.logger.info("Mic Service cleaned up cleanly.")
        
    def stop(self) -> None:
        """Signal the service to stop."""
        super().stop()
        
    def update(self) -> None:
        """
        Update is not strictly required here if another component consumes via `read_mic()`, 
        but we implement it to satisfy BaseService abstract method.
        """
        pass
