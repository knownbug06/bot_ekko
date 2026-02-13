import pygame
import sys
import os
import random

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot_ekko.core.state_machine import StateMachine
from bot_ekko.ui_expressions_lib.eyes.adapter import EyesExpressionAdapter
from bot_ekko.sys_config import LOGICAL_W, LOGICAL_H, STATES

def verify_expressions():
    pygame.init()
    
    # Create dummy surface
    surface = pygame.Surface((LOGICAL_W, LOGICAL_H))
    
    # Init components
    state_machine = StateMachine()
    adapter = EyesExpressionAdapter(state_machine)
    
    # Mock dependencies
    class MockHandler:
        def __init__(self, sm):
            self.state_machine = sm
            self.current_state_params = {}
            self.state_entry_time = 0
            
        def get_state(self):
            return self.state_machine.get_state()
            
    class MockCommandCenter:
        def issue_command(self, cmd, params=None):
            print(f"Command issued: {cmd} {params}")
            
    state_handler = MockHandler(state_machine)
    command_center = MockCommandCenter()
    
    adapter.set_dependencies(state_handler, command_center)
    
    # Test new states
    new_states = ["SAD", "CONFUSED", "CRYING", "EXCITED", "AMUSED", "SURPRISED"]
    
    for state in new_states:
        print(f"Testing state: {state}")
        
        # Set state
        state_machine.set_state(state)
        state_handler.state_entry_time = pygame.time.get_ticks()
        
        # Run a few updates to let physics settle/move
        for i in range(10):
            now = pygame.time.get_ticks() + i * 16
            adapter.update(now)
            
        # Render
        try:
            surface.fill((0, 0, 0))
            adapter.render(surface, pygame.time.get_ticks())
            print(f"  Rendered {state} successfully")
        except Exception as e:
            print(f"  FAILED to render {state}: {e}")
            sys.exit(1)
            
    print("\nAll new expressions verified!")

if __name__ == "__main__":
    verify_expressions()
