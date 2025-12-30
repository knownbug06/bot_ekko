class Looks:
    def __init__(self, eyes, state_machine):
        self.eyes = eyes
        self.state_machine = state_machine
    
    def look_left(self):
        x = -100
        y = 20
        self.eyes.set_look_at(x, y)
    
    def look_right(self):
        x = 100
        y = 20
        self.eyes.set_look_at(x, y)
    
    def look_up(self):
        x = 0
        y = -100
        self.eyes.set_look_at(x, y)
    
    def look_down(self):
        x = 0
        y = 100
        self.eyes.set_look_at(x, y)
    
    def look_up_left(self):
        x = -100
        y = -100
        self.eyes.set_look_at(x, y)
    
    def look_up_right(self):
        x = 100
        y = -100
        self.eyes.set_look_at(x, y)
    
    def look_down_left(self):
        x = -100
        y = 100
        self.eyes.set_look_at(x, y)
    
    def look_down_right(self):
        x = 100
        y = 100
        self.eyes.set_look_at(x, y)
    
    def look_center(self):
        x = 0
        y = 0
        self.eyes.set_look_at(x, y)
    


