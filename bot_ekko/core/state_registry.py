from typing import Dict, List, Optional, Any
from bot_ekko.core.logger import get_logger

logger = get_logger("StateRegistry")

class StateRegistry:
    # State Constants
    ACTIVE = "ACTIVE"
    SQUINTING = "SQUINTING"
    SLEEPING = "SLEEPING"
    WAKING = "WAKING"
    CONFUSED = "CONFUSED"
    THINKING = "THINKING"
    ANGRY = "ANGRY"
    SCARED = "SCARED"
    HAPPY = "HAPPY"
    RAINBOW_EYES = "RAINBOW_EYES"
    WINK = "WINK"
    UWU = "UWU"
    SAD = "SAD"
    CRYING = "CRYING"
    EXCITED = "EXCITED"
    AMUSED = "AMUSED"
    SURPRISED = "SURPRISED"
    CANVAS = "CANVAS"
    CHAT = "CHAT"
    CLOCK = "CLOCK"

    # Internal storage for state data
    # Initialized with None for known states
    _data: Dict[str, Optional[Any]] = {
        ACTIVE: None,
        SQUINTING: None,
        SLEEPING: None,
        WAKING: None,
        CONFUSED: None,
        THINKING: None,
        ANGRY: None,
        SCARED: None,
        HAPPY: None,
        RAINBOW_EYES: None,
        WINK: None,
        UWU: None,
        SAD: None,
        CRYING: None,
        EXCITED: None,
        AMUSED: None,
        SURPRISED: None,
        CANVAS: None,
        CHAT: None,
        CLOCK: None,
    }

    @classmethod
    def register_state(cls, name: str, data: Any) -> None:
        """
        Register or update data for a state.
        
        Args:
            name (str): The name of the state.
            data (Any): The data associated with the state.
        """
        cls._data[name] = data
        logger.debug(f"Registered state data for: {name}")

    @classmethod
    def get_state_data(cls, name: str) -> Optional[Any]:
        """
        Get data associated with a state.
        
        Args:
            name (str): The name of the state.
            
        Returns:
            Optional[Any]: The data associated with the state, or None if not found/set.
        """
        return cls._data.get(name)

    @classmethod
    def has_state(cls, name: str) -> bool:
        """
        Check if a state exists in the registry (even if data is None).
        
        Args:
            name (str): The name of the state.
            
        Returns:
            bool: True if the state key exists.
        """
        return name in cls._data
