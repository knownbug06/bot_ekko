# ekko_vision/ipc_server.py
import socket
import os
import struct
import json
import threading
import logging

from bot_ekko.core.logger import get_logger

logger = get_logger(__name__)


class IPCServer:
    def __init__(self, socket_path: str, handler):
        self.socket_path = socket_path
        self.handler = handler
        self.sock = None
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        logger.info(f"Starting IPC server on {self.socket_path}")
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.socket_path)
        self.sock.listen(5)

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )
        self._thread.start()

        logger.info(f"IPC server listening on {self.socket_path}")

    def _run(self):
        while not self._stop.is_set():
            try:
                logger.info("Waiting for connection...")
                conn, _ = self.sock.accept()
                logger.info("Accepted connection!")
                self._handle_client(conn)
                logger.info("Client disconnected.")
            except OSError:
                break

    def _handle_client(self, conn):
        with conn:
            while True:
                print('listening')
                hdr = self._recv_exact(conn, 4)
                if not hdr:
                    return

                length = struct.unpack(">I", hdr)[0]
                payload = self._recv_exact(conn, length)
                if not payload:
                    return

                try:
                    msg = json.loads(payload.decode("utf-8"))
                    self.handler(msg)
                except Exception as e:
                    logger.error(f"Bad message: {e}")

    def _recv_exact(self, conn, n):
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def stop(self):
        self._stop.set()
        if self.sock:
            self.sock.close()
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
