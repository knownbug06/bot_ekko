import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
import multiprocessing
from bot_ekko.core.errors import (
    ServiceInitializationError,
    ServiceDependencyError
)
from bot_ekko.core.logger import get_logger
import pygame

class ServiceStatus(Enum):
    """Enumeration for service lifecycle statuses."""
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
        """
        Initialize the BaseService.

        Args:
            name (str): Name of the service.
            enabled (bool, optional): Whether the service is enabled by default. Defaults to False.
        """
        self.service_name = name
        self.logger = get_logger(f"service.{name}")
        self._status = ServiceStatus.NOT_INITIALIZED
        self._stats: Dict[str, Any] = {}
        self._service_initialized = False
        self._enabled = enabled
    
    @property
    def enabled(self) -> bool:
        """bool: Whether the service is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def status(self) -> ServiceStatus:
        """ServiceStatus: The current status of the service."""
        return self._status

    @property
    def stats(self) -> Dict[str, Any]:
        """Dict[str, Any]: A copy of the service statistics."""
        return self._stats.copy()

    def update_stat(self, key: str, value: Any) -> None:
        """
        Update a statistic value.

        Args:
            key (str): The statistic name.
            value (Any): The value to set.
        """
        self._stats[key] = value

    def increment_stat(self, key: str, amount: int = 1) -> None:
        """
        Increment a numeric statistic.

        Args:
            key (str): The statistic name.
            amount (int, optional): Amount to increment by. Defaults to 1.
        """
        current = self._stats.get(key, 0)
        if isinstance(current, (int, float)):
            self._stats[key] = current + amount
        else:
            self.logger.warning(f"Cannot increment non-numeric stat: {key}")

    def set_status(self, status: ServiceStatus) -> None:
        """
        Update service status and log the change.

        Args:
            status (ServiceStatus): The new status.
        """
        self._status = status
        self.logger.info(f"Service: {self.service_name} status changed to: {status.value}")

    def init(self) -> None:
        """
        Initialize the service resources. 
        Can be called manually to retry initialization.
        Subclasses should allow this to be called multiple times if needed,
        or check self._initialized.
        """
        self._service_initialized = True
        self._status = ServiceStatus.INITIALIZED
        self.logger.info(f"Service: {self.service_name} initialized")

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
        """Update the service. Called in the main loop."""
        pass
    

class Service(BaseService):
    """
    Standard non-threaded service.
    Useful for synchronous tasks or services managed externally.
    """
    def start(self) -> None:
        """Starts the service (synchronous)."""
        if not self._service_initialized:
            self.init()
        self.set_status(ServiceStatus.RUNNING)

    def stop(self) -> None:
        """Stops the service."""
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
        """
        Start the service thread.
        Auto-initializes if not already initialized.
        """
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
        self.set_status(ServiceStatus.STOPPED)
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
            self.update_stat("last_error", str(e))
            # We don't re-raise here typically as it's a separate thread

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
        if not self._service_initialized:
            try:
                self.init()
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


class BasePhysicsEngine(ABC):

    def __init__(self):
        self.target_x, self.target_y = 0, 0
        self.last_gaze = 0
    
    
    def set_look_at(self, x: int, y: int) -> None:
        """
        Manually set where the eyes should look relative to center.
        
        Args:
            x (int): Horizontal offset from center.
            y (int): Vertical offset from center.
        """
        self.target_x = x
        self.target_y = y
        self.last_gaze = pygame.time.get_ticks()
        logger.debug(f"Eyes set to look at ({x}, {y})")
        
from abc import abstractmethod
from datetime import datetime
import pygame
from bot_ekko.core.render_engine import AbstractRenderEngine
from bot_ekko.core.state_registry import StateRegistry
from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import CommandNames
from bot_ekko.core.scheduler import Scheduler
from bot_ekko.sys_config import SCHEDULE_FILE_PATH

logger = get_logger("BaseStateRenderer")

class BaseStateRenderer(AbstractRenderEngine):
    """
    Base class for state-based renderers.
    Handles scheduling and dynamic dispatch to state handlers.
    """
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.state_handler = None
        self.command_center = None
        self.scheduler = Scheduler(SCHEDULE_FILE_PATH)

    def set_dependencies(self, state_handler, command_center):
        self.state_handler = state_handler
        self.command_center = command_center

    def update(self, now: int) -> None:
        """
        Update logic. Subclasses should call super().update(now) or implement their own
        and call _check_schedule manually if needed.
        """
        self._check_schedule(now)

    def render(self, surface: pygame.Surface, now: int) -> None:
        """
        Main render loop.
        Dispatches to handle_<STATE_NAME> methods.
        """
        if not self.state_handler:
            return

        current_state = self.state_handler.get_state().upper()
        handler_name = f"handle_{current_state}"
        handler = getattr(self, handler_name, None)

        if handler:
            handler(surface, now, params=self.state_handler.current_state_params)
        else:
            logger.warning(f"Warning: No handler for state {current_state}")
            self.handle_fallback(surface, now)

    def handle_fallback(self, surface: pygame.Surface, now: int):
        """
        Called when no specific handler exists for the current state.
        Subclasses should override this.
        """
        pass

    def _check_schedule(self, now):
        # Grace period on startup (2 seconds) to ensure we start in ACTIVE/Initial state
        if now < 2000:
            return

        current_state = self.state_handler.get_state()
        if current_state == StateRegistry.CHAT:
            return

        now_dt = datetime.now()
        
        result = self.scheduler.get_target_state(now_dt, current_state)

        if result:
            target_state, params = result
            
            # Prepare params with source tracking
            cmd_params = params.copy() if params else {}
            cmd_params["_source"] = "scheduler"
            cmd_params["target_state"] = target_state
            
            # Scheduler says we should be in target_state
            if current_state != target_state:
                logger.info(f"Triggering {target_state} state from schedule with params: {params}")
                self.command_center.issue_command(CommandNames.CHANGE_STATE, params=cmd_params)
        else:
            # No active schedule
            # Check if we are currently in a state triggered by the scheduler
            current_params = self.state_handler.current_state_params or {}
            
            # Helper to handle case where params might be flattened or nested (defensive)
            source = current_params.get("_source") if isinstance(current_params, dict) else None
            
            if source == "scheduler":
                if current_state == StateRegistry.SLEEPING:
                     logger.info("Triggering WAKING state (Schedule ended)")
                     self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": StateRegistry.WAKING})
                else:
                     logger.info(f"Reverting to ACTIVE from {current_state} (Schedule ended)")
                     self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": StateRegistry.ACTIVE})
