class StateMachine:
    def __init__(self, initial_state="ACTIVE"):
        self.state = initial_state
        self.history = []
    
    def set_state(self, new_state):
        if self.state != new_state:
            print(f"State transition: {self.state} -> {new_state}")
            self.state = new_state
    
    def get_state(self):
        return self.state

    def store_context(self):
        """Saves current state to history."""
        if len(self.history) > 50:
            self.history.pop(0)
        self.history.append(self.state)

    def restore_context(self):
        """Restores the last state from history."""
        if self.history:
            prev_state = self.history.pop()
            self.set_state(prev_state)
            print(f"Context restored to: {prev_state}")
