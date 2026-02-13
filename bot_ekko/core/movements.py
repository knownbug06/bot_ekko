import pygame
from bot_ekko.core.base import BasePhysicsEngine


class BaseMovements:
    """
    Base class for physics modules affecting facial features.
    Handles common gaze direction logic.
    """

    DIRECTIONS = {
        "LEFT": (-60, 0),
        "RIGHT": (60, 0),
        "UP": (0, -40),
        "DOWN": (0, 40),
        "CENTER": (0, 0),
        "UP_LEFT": (-60, -40),
        "UP_RIGHT": (60, -40),
        "DOWN_LEFT": (-60, 40),
        "DOWN_RIGHT": (60, 40)
    }

    def __init__(self, physics_engine: BasePhysicsEngine):
        self.physics_engine = physics_engine


    def look_at(self, direction: str) -> None:
        """
        Look at a specific named direction.
        
        Args:
            direction (str): Name of the direction (e.g., "LEFT", "UP_RIGHT").
        """
        coords = self.DIRECTIONS.get(direction.upper())
        if coords:
            self.physics_engine.set_look_at(*coords)

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
