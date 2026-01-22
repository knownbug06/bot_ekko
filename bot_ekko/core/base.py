import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict
import multiprocessing
from bot_ekko.core.errors import (
    ServiceInitializationError
)
from bot_ekko.core.logger import get_logger

class ServiceStatus(Enum):
    NOT_INITIALIZED = "NOT_INITIALIZED"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class BaseService(ABC):
    """
    Base class for all services.
    Provides basic status tracking and stats capabilities.
    """
    def __init__(self, name: str, enabled: bool = False):
        self.service_name = name
        self.logger = get_logger(f"service.{name}")
        self._status = ServiceStatus.NOT_INITIALIZED
        self._stats: Dict[str, Any] = {}
        self._service_initialized = False
        self._enabled = enabled
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @property
    def status(self) -> ServiceStatus:
        return self._status

    @property
    def stats(self) -> Dict[str, Any]:
        return self._stats.copy()

    def update_stat(self, key: str, value: Any) -> None:
        """Update a statistic value."""
        self._stats[key] = value

    def increment_stat(self, key: str, amount: int = 1) -> None:
        """Increment a numeric statistic."""
        current = self._stats.get(key, 0)
        if isinstance(current, (int, float)):
            self._stats[key] = current + amount
        else:
            self.logger.warning(f"Cannot increment non-numeric stat: {key}")

    def set_status(self, status: ServiceStatus) -> None:
        """Update service status."""
        self._status = status
        self.logger.info(f"Service status changed to: {status.value}")

    def init(self) -> None:
        """
        Initialize the service resources. 
        Can be called manually to retry initialization.
        Subclasses should allow this to be called multiple times if needed, 
        or check self._initialized.
        """
        self._service_initialized = True
        self._status = ServiceStatus.INITIALIZED
        self.logger.info("Service initialized")

    @abstractmethod
    def start(self) -> None:
        """Start the service."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the service."""
        pass

    @abstractmethod
    def update(self) -> None:
        """Update the service."""
        pass
    

class Service(BaseService):
    """
    Standard non-threaded service.
    Useful for synchronous tasks or services managed externally.
    """
    def start(self) -> None:
        if not self._service_initialized:
            self.init()
        self.set_status(ServiceStatus.RUNNING)

    def stop(self) -> None:
        self.set_status(ServiceStatus.STOPPED)

class ThreadedService(BaseService, threading.Thread):
    """
    Service that runs in its own thread.
    """
    def __init__(self, name: str, enabled: bool = False, daemon: bool = True):
        BaseService.__init__(self, name, enabled=enabled)
        threading.Thread.__init__(self, name=name, daemon=daemon)
        self._stop_event = threading.Event()

    def init(self) -> None:
        super().init()

    def start(self) -> None:
        """Start the service thread."""
        if not self._service_initialized:
            try:
                self.init()
            except Exception as e:
                self.logger.error(f"Failed to auto-initialize service: {e}")
                self.set_status(ServiceStatus.ERROR)
                # propogate exception
                raise e
        else:
            self.logger.info("Service already initialized")

        if self._status == ServiceStatus.RUNNING:
            self.logger.warning("Service is already running")
            return
        
        # We need to call threading.Thread.start() explicitly because BaseService is first in MRO
        threading.Thread.start(self)

    def stop(self) -> None:
        """Signal the service to stop."""
        self.logger.info("Stopping service...")
        self._stop_event.set()
        # Wait for thread to finish if needed, or let the caller join()

    def run(self) -> None:
        """Main thread loop wrapper."""
        self.set_status(ServiceStatus.RUNNING)
        try:
            self._run()
        except Exception as e:
            self.logger.error(f"Service crashed: {e}", exc_info=True)
            self.set_status(ServiceStatus.ERROR)
        except Exception as e:
            self.logger.error(f"Service crashed: {e}", exc_info=True)
            self.set_status(ServiceStatus.ERROR)
            self.update_stat("last_error", str(e))
            # We don't re-raise here typically as it's a separate thread

        else:
            self.set_status(ServiceStatus.STOPPED)

    @abstractmethod
    def _run(self) -> None:
        """
        Implementation of the service logic.
        Should periodically check self._stop_event.is_set()
        """
        pass


class ProcessService(BaseService, multiprocessing.Process):
    """
    Service that runs in its own process.
    """
    def __init__(self, name: str, daemon: bool = True):
        BaseService.__init__(self, name)
        multiprocessing.Process.__init__(self, name=name, daemon=daemon)
        self._stop_event = multiprocessing.Event()

    @property
    def status(self) -> ServiceStatus:
        if self.is_alive():
            return ServiceStatus.RUNNING
        return self._status

    def init(self) -> None:
        super().init()

    def start(self) -> None:
        """Start the service process."""
        if not self._initialized:
            try:
                self.init()
            except Exception as e:
                self.logger.error(f"Failed to auto-initialize service: {e}")
            except Exception as e:
                self.logger.error(f"Failed to auto-initialize service: {e}")
                raise ServiceInitializationError(f"Failed to auto-initialize: {e}", self.name) from e

        if self.is_alive():
            self.logger.warning("Service is already running")
            return
            
        multiprocessing.Process.start(self)
        # Optimistically set status in parent, though property uses is_alive()
        self.set_status(ServiceStatus.RUNNING)

    def stop(self) -> None:
        """Signal the service to stop."""
        self.logger.info("Stopping service...")
        self._stop_event.set()
        # We don't verify stop here, caller should join() or check status
    
    def run(self) -> None:
        """Main process loop wrapper."""
        # Note: In child process, self._status updates are local
        self.set_status(ServiceStatus.RUNNING)
        try:
            self._run()
        except Exception as e:
            # Basic logging to stderr/stdout as logger might not be configured for MP
            print(f"ProcessService {self.name} crashed: {e}")
            self.set_status(ServiceStatus.ERROR)
            self.update_stat("last_error", str(e))
        else:
            self.set_status(ServiceStatus.STOPPED)

    @abstractmethod
    def _run(self) -> None:
        """
        Implementation of the service logic.
        Should periodically check self._stop_event.is_set()
        """
        pass
