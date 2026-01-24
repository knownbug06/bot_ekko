
import socket
import struct
import json
import time

from bot_ekko.sys_config import GESTURE_DETECTION_IPC_SOCKET_PATH


SOCKET_PATH = GESTURE_DETECTION_IPC_SOCKET_PATH

def send_gesture(payload: dict):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(SOCKET_PATH)
        print(f"Connected to {SOCKET_PATH}")
        
        payload = json.dumps(payload).encode("utf-8")
        header = struct.pack(">I", len(payload))
        
        client.sendall(header + payload)
        print(f"Sent: {payload}")
        
        time.sleep(0.1) # Give server time to read
        return True
        
    except FileNotFoundError:
        print(f"Socket not found at {SOCKET_PATH}. Is the bot running?")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the bot running?")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    send_gesture({"gesture": "wave", "score": 0.95})
