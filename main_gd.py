import time
from bot_ekko.vision.gesture_detection.detector import GestureDetection


if __name__ == "__main__":
    gd = GestureDetection(show_window=False)
    try:
        gd.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        gd.stop()