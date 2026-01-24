from typing import Any

class Looks:
    """
    Defines preset eye lookup directions and convenience methods for eye movement.
    """
    
    # Preset coordinates for specific look directions: (x, y)
    DIRECTIONS = {
        "LEFT": (-100, 20),
        "RIGHT": (100, 20),
        "UP": (0, -100),
        "DOWN": (0, 100),
        "UP_LEFT": (-100, -100),
        "UP_RIGHT": (100, -100),
        "DOWN_LEFT": (-100, 100),
        "DOWN_RIGHT": (100, 100),
        "CENTER": (0, 0)
    }

    def __init__(self, eyes: Any, state_machine: Any):
        """
        Initialize the Looks helper.

        Args:
            eyes: The Eyes controller instance.
            state_machine: The StateMachine instance.
        """
        self.eyes = eyes
        self.state_machine = state_machine
    
    def look_at(self, direction: str) -> None:
        """
        Look at a specific named direction.
        
        Args:
            direction (str): Name of the direction (e.g., "LEFT", "UP_RIGHT").
        """
        coords = self.DIRECTIONS.get(direction.upper())
        if coords:
            self.eyes.set_look_at(*coords)

    def look_left(self) -> None:
        self.look_at("LEFT")
    
    def look_right(self) -> None:
        self.look_at("RIGHT")
    
    def look_up(self) -> None:
        self.look_at("UP")
    
    def look_down(self) -> None:
        self.look_at("DOWN")
    
    def look_up_left(self) -> None:
        self.look_at("UP_LEFT")
    
    def look_up_right(self) -> None:
        self.look_at("UP_RIGHT")
    
    def look_down_left(self) -> None:
        self.look_at("DOWN_LEFT")
    
    def look_down_right(self) -> None:
        self.look_at("DOWN_RIGHT")
    
    def look_center(self) -> None:
        self.look_at("CENTER")
