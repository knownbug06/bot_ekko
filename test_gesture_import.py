
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add the project root to python path so we can import modules
sys.path.append("/home/ekko/mainbot/bot_ekko")

try:
    from bot_ekko.vision.gesture_detection.gesture_triggers import GestureDetection
    from bot_ekko.core.command_center import CommandCenter
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

class TestGestureDetection(unittest.TestCase):
    def test_init(self):
        mock_cc = MagicMock(spec=CommandCenter)
        gd = GestureDetection(mock_cc)
        self.assertIsNotNone(gd)
        self.assertEqual(gd.socket_path, "/tmp/ekk-_bot.sock")
        print("GestureDetection initialized successfully")

if __name__ == "__main__":
    unittest.main()
