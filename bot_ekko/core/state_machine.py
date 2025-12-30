from bot_ekko.core.logger import get_logger

logger = get_logger("StateMachine")

class StateMachine:
    def __init__(self, initial_state="ACTIVE"):
        self.state = initial_state
        self.history = set()
    
    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
    
    def get_state(self):
        return self.state

    def store_context(self):
        """Saves current state to history."""
        if len(self.history) > 50:
            self.history.pop()
        self.history.add(self.state)

    def restore_context(self):
        """Restores the last state from history."""
        if self.history:
            prev_state = self.history.pop()
            self.set_state(prev_state)
            logger.info(f"Context restored to: {prev_state}")
