import socket
import struct
import json
import time

SOCKET_PATH = "/tmp/ekko_ipc.sock"

def send_gesture(gesture, score):
    print(f"Sending gesture: {gesture}, score: {score}")
    payload = json.dumps({"gesture": gesture, "score": score}).encode('utf-8')
    length = len(payload)
    
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        
        # Send length (4 bytes big-endian)
        sock.sendall(struct.pack(">I", length))
        # Send payload
        sock.sendall(payload)
        
        sock.close()
        print("Sent successfully")
    except Exception as e:
        print(f"Error sending: {e}")

if __name__ == "__main__":
    print("Testing Vision Service Socket...")
    time.sleep(1)
    
    # Test 1: Thumb Up -> HAPPY
    send_gesture("thumb_up", 0.95)
    time.sleep(2)
    
    # Test 2: Thumb Down -> ANGRY
    send_gesture("thumb_down", 0.8)
    time.sleep(2)
    
    # Test 3: Victory -> UWU
    send_gesture("victory", 0.99)
    time.sleep(2)
    
    print("Test complete.")
