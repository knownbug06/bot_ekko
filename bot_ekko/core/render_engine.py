from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from typing import Any
import pygame

class AbstractRenderEngine(ABC):
    """
    Abstract base class for all render engines.
    A Render Engine is responsible for:
    1. Managing the visual representation (drawing to surface).
    2. Handling the physics/logic of the specific visualization (e.g., eye movement).
    3. Providing state context for saving/restoring (e.g., eye position).
    """

    @abstractmethod
    def render(self, surface: pygame.Surface, now: int) -> None:
        """
        Render the current state to the provided surface.
        
        Args:
            surface (pygame.Surface): The surface to draw on.
            now (int): Current timestamp in milliseconds.
        """
        pass

    @abstractmethod
    def update(self, now: int) -> None:
        """
        Update internal physics or logic. 
        Should be called every frame before render.
        
        Args:
            now (int): Current timestamp in milliseconds.
        """
        pass

    @abstractmethod
    def get_physics_state(self) -> Dict[str, Any]:
        """
        Capture the current physical state (e.g., coordinates, velocity).
        Used for context saving.
        
        Returns:
            Dict[str, Any]: A serializable dictionary of the state.
        """
        pass

    @abstractmethod
    def set_physics_state(self, state: Dict[str, Any]) -> None:
        """
        Restore the physical state from a saved context.
        
        Args:
            state (Dict[str, Any]): The state dictionary to restore.
        """
        pass
    @abstractmethod
    def set_dependencies(self, state_handler: Any, command_center: Any) -> None:
        """
        Inject dependencies that are created after the engine.
        
        Args:
            state_handler (BaseStateHandler): The state handler instance.
            command_center (CommandCenter): The command center instance.
        """
        pass
