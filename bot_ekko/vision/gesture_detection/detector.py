import time
import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2 # Needed to fix the drawing error
from picamera2 import Picamera2

from bot_ekko.vision.gesture_detection.ipc_client import send_gesture
from bot_ekko.core.logger import get_logger
from bot_ekko.sys_config import GESTURE_DETECTION_MODEL_PATH

logger = get_logger(__name__)


# Force X11/XCB for SSH window stability
os.environ["QT_QPA_PLATFORM"] = "xcb"


class GestureDetection:
    def __init__(self, show_window=True):
        self.running = False
        self.show_window = show_window
        
        # Setup Legacy Drawing Utilities
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_hands = mp.solutions.hands

        # 1. Initialize Gesture Recognizer
        base_options = python.BaseOptions(model_asset_path=GESTURE_DETECTION_MODEL_PATH)
        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO
        )
        self.recognizer = vision.GestureRecognizer.create_from_options(options)

        # 2. Setup PiCamera2 (Reduced resolution for faster SSH display)
        self.picam2 = Picamera2()
        config = self.picam2.create_video_configuration(main={"format": 'RGB888', "size": (640, 480)})
        self.picam2.configure(config)

    def start(self):
        self.picam2.start()
        self.running = True
        logger.info("Ekko Vision Active. Connect via 'ssh -Y' to see the window.")
        self._run_loop()

    def stop(self):
        self.running = False
        self.picam2.stop()
        self.recognizer.close()
        cv2.destroyAllWindows()

    def _run_loop(self):
        while self.running:
            frame = self.picam2.capture_array()
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            frame = cv2.flip(frame, 1)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            timestamp_ms = int(time.time() * 1000)
            
            result = self.recognizer.recognize_for_video(mp_image, timestamp_ms)

            if self.show_window:
                debug_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # FIX: Convert the Result List to a Landmark Proto for drawing
                if result.hand_landmarks:
                    for hand_landmarks in result.hand_landmarks:
                        # Create a HandLandmarks proto object from the list
                        hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                        hand_landmarks_proto.landmark.extend([
                            landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) 
                            for landmark in hand_landmarks
                        ])
                        
                        self.mp_drawing.draw_landmarks(
                            debug_frame,
                            hand_landmarks_proto, # Use the converted proto here
                            self.mp_hands.HAND_CONNECTIONS,
                            self.mp_drawing_styles.get_default_hand_landmarks_style(),
                            self.mp_drawing_styles.get_default_hand_connections_style())

                cv2.imshow('Ekko Bot Vision', debug_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # Send IPC data
            if result.gestures:
                gesture = result.gestures[0][0]
                if gesture.score > 0.65:
                    payload = {"gesture": gesture.category_name, "score": gesture.score}
                    print(f"Gesture detected: {payload}")
                    if send_gesture(payload):
                        logger.info(f"Gesture sent: {payload}")

        self.stop()

