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
