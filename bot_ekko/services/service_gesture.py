import json
import socket
import struct
import os
import time
from typing import Optional, Dict

from bot_ekko.core.base import ThreadedService, ServiceStatus
from bot_ekko.core.models import GestureData, CommandNames, ServiceGestureConfig
from bot_ekko.core.command_center import CommandCenter

class GestureService(ThreadedService):
    """
    Service to handle gesture input via a Unix Domain Socket.
    Receives JSON payloads from an external gesture recognition process.
    """
    def __init__(self, command_center: CommandCenter, service_gesture_config: ServiceGestureConfig) -> None:
        """
        Initialize the Gesture Service.

        Args:
            command_center (CommandCenter): Command issuer.
            service_gesture_config (ServiceGestureConfig): Configuration.
        """
        super().__init__(service_gesture_config.name, enabled=service_gesture_config.enabled)

        self.socket_path = service_gesture_config.socket_path
        self.command_center = command_center
        self.service_config = service_gesture_config
        
        self.sock: Optional[socket.socket] = None

        # Default mapping if not provided in config
        self._gesture_state_mapping = service_gesture_config.gesture_state_mapping
        
        # Initialize empty vision data
        self.vision_data = GestureData(
            gesture="",
            score=0.0,
            status="NA"
        )
        
        self._last_processed_gesture: Optional[str] = None
        self._last_processed_time = 0

    def init(self) -> None:
        """Initialize socket server."""
        self.logger.info(f"Initializing Gesture Service socket on {self.socket_path}")

        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)

            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.bind(self.socket_path)
            self.sock.listen(5)
            # Make socket non-blocking so we can check stop event
            self.sock.settimeout(1.0) 
            
            super().init()
        except Exception as e:
            self.logger.error(f"Gesture Service Init Error: {e}")
            self.update_stat("init_error", str(e))

            self.set_status(ServiceStatus.ERROR)
            raise e

    def _run(self) -> None:
        """
        Main service loop.
        Accepts connections and reads data.
        """
        if not self.sock:
            self.logger.error("Gesture Service running without active socket.")
            return

        self.logger.info("Gesture Service Loop Started")

        while not self._stop_event.is_set():
            try:
                # Accept connection
                try:
                    conn, _ = self.sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                
                self.logger.debug("Gesture client connected")

                with conn:
                    conn.settimeout(1.0) # Timeout for recv
                    while not self._stop_event.is_set():
                        # Read header (4 bytes length)
                        try:
                            hdr = self._recv_exact(conn, 4)
                            if not hdr:
                                break
                            
                            length = struct.unpack(">I", hdr)[0]
                            payload = self._recv_exact(conn, length)
                            if not payload:
                                break
                            
                            msg = json.loads(payload.decode("utf-8"))
                            
                            # Update stats
                            self.increment_stat("messages_received")
                            
                            # Parse message
                            # Expected format: {"gesture": "name", "score": 0.9}
                            gesture = msg.get("gesture", "").lower()
                            score = float(msg.get("score", 0.0))
                            
                            # Update internal data
                            self.vision_data = GestureData(
                                gesture=gesture,
                                score=score,
                                status="ok"
                            )
                            
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            self.increment_stat("decode_errors")
                            continue
                        except socket.timeout:
                            continue
                        except Exception as e:
                            self.logger.error(f"Gesture Loop Error: {e}")
                            self.increment_stat("processing_errors")
                            break
                            
                self.logger.debug("Gesture client disconnected")

            except Exception as e:
                self.logger.error(f"Critical Gesture Loop Error: {e}")
                self.set_status(ServiceStatus.ERROR)

                time.sleep(1)

    def _recv_exact(self, conn: socket.socket, n: int) -> Optional[bytes]:
        """
        Reads exactly n bytes from the socket.

        Args:
            conn (socket.socket): The connection object.
            n (int): Number of bytes to read.

        Returns:
            Optional[bytes]: The read bytes, or None if EOF/Timeout/Stop.
        """
        buf = b""
        while len(buf) < n:
            try:
                chunk = conn.recv(n - len(buf))
                if not chunk:
                    return None
                buf += chunk
            except socket.timeout:
                if self._stop_event.is_set():
                    return None
                continue
        return buf

    def stop(self) -> None:
        """Stops the socket service."""
        super().stop()
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                self.logger.error(f"Error closing socket: {e}")
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except Exception: # pylint: disable=broad-except
                pass
    
    def update(self) -> None:
        """
        Check for gesture changes and trigger commands.
        """
        # Logic similar to original gesture_triggers.py
        current_data = self.vision_data
        
        if current_data.status != "ok":
            return
            
        gesture = current_data.gesture
        
        if not gesture:
            return

        if gesture == self._last_processed_gesture:
            return
        
        self.logger.info(f"Processing new gesture '{gesture}' with score {current_data.score}")
        self._last_processed_gesture = gesture
        
        if gesture in self._gesture_state_mapping:
            target_state = self._gesture_state_mapping[gesture]
            self.command_center.issue_command(
                CommandNames.CHANGE_STATE, 
                params={"target_state": target_state, "score": current_data.score}
            )

