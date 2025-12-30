from bot_ekko.core.logger import get_logger


logger = get_logger("StateMachine")

class StateMachine:
    def __init__(self, initial_state="ACTIVE"):
        self.state = initial_state
    
    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
    
    def get_state(self):
        return self.state
