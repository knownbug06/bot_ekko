import pytest
import time
import threading
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot_ekko.services.base import Service, ThreadedService

class MockService(Service):
    def start(self) -> None:
        super().start()

    def stop(self) -> None:
        super().stop()

class MockThreadedService(ThreadedService):
    def __init__(self, name: str):
        super().__init__(name)
        self.run_count = 0

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.run_count += 1
            time.sleep(0.01)

@pytest.fixture
def mock_service_cls():
    return MockService

@pytest.fixture
def mock_threaded_service_cls():
    return MockThreadedService

@pytest.fixture
def base_service():
    return MockService("test_service")

@pytest.fixture
def threaded_service():
    return MockThreadedService("threaded_test_service")
