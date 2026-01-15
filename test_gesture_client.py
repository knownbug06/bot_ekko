
import socket
import struct
import json
import time

SOCKET_PATH = "/tmp/ekko_ipc.sock"

def send_gesture(gesture, score):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(SOCKET_PATH)
        print(f"Connected to {SOCKET_PATH}")
        
        payload = json.dumps({"gesture": gesture, "score": score}).encode("utf-8")
        header = struct.pack(">I", len(payload))
        
        client.sendall(header + payload)
        print(f"Sent: {gesture}, {score}")
        
        time.sleep(0.1) # Give server time to read
        
    except FileNotFoundError:
        print(f"Socket not found at {SOCKET_PATH}. Is the bot running?")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the bot running?")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    send_gesture("wave", 0.95)
