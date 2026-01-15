from bot_ekko.core.logger import get_logger
from bot_ekko.ipc.unix_ipc.ipc_server import IPCServer
from bot_ekko.core.command_center import CommandCenter
from bot_ekko.core.models import CommandNames

logger = get_logger("GestureDetection")

class GestureDetection:
    def __init__(self, command_center: CommandCenter):
        self.command_center = command_center
        # Using /tmp/ekk-_bot.sock as the default socket path
        self.socket_path = "/tmp/ekko_ipc.sock"
        self.server = IPCServer(self.socket_path, self._handle_gesture_payload)

        self._gesture_state_mapping = {
            "thumb_up": "HAPPY",
            "thumb_down": "RAINBOW_EYES",
            "closed_fist": "ACTIVE"
        }

        self._last_gesture = None
        
    def start(self):
        logger.info(f"Starting Gesture Detection IPC Server on {self.socket_path}")
        self.server.start()
        
    def stop(self):
        logger.info(f"Stopping Gesture Detection IPC Server on {self.socket_path}")
        self.server.stop()

    def _handle_gesture_payload(self, payload: dict):
        """
        Callback for IPCServer when a message is received.
        Payload format: {"gesture": "name", "score": "value"}
        """
        logger.info(f"Received gesture payload: {payload}")
        
        gesture = payload.get("gesture", '').lower()
        score = payload.get("score")
        
        if not gesture:
            logger.warning(f"Invalid payload: missing 'gesture' field")
            return
        
        if gesture == self._last_gesture:
            return
        
        self._last_gesture = gesture
            
        self._process_gesture(gesture, score)
        
    def _process_gesture(self, gesture: str, score):
        """
        Map gestures to commands.
        """
        logger.info(f"Processing gesture '{gesture}' with score {score}")
        if gesture not in self._gesture_state_mapping:
            return
        
        target_state = self._gesture_state_mapping[gesture]
        self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": target_state, "score": score})
        
