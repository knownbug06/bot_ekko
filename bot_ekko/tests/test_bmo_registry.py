import sys
import os
import pygame

# Dynamic path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(package_root)

# If running from inside bot_ekko/bot_ekko, package_root is .../bot_ekko
if package_root not in sys.path:
    sys.path.insert(0, package_root)

try:
    from bot_ekko.core.state_registry import StateRegistry
    from bot_ekko.ui_expressions_lib.bmo.adapter import BMOAdapter
    from bot_ekko.core.state_machine import StateMachine
    from bot_ekko.core.state_machine import StateHandler
except ImportError:
    # Try appending just the parent
    parent = os.path.dirname(current_dir)
    sys.path.insert(0, os.path.dirname(parent))
    from bot_ekko.core.state_registry import StateRegistry
    from bot_ekko.ui_expressions_lib.bmo.adapter import BMOAdapter
    from bot_ekko.core.state_machine import StateMachine
    from bot_ekko.core.state_machine import StateHandler

def test_bmo_registry():
    print("Testing BMO Registry...")
    
    # 1. Instantiate Adapter
    print("Instantiating BMOAdapter...")
    try:
        sm = StateMachine()
        adapter = BMOAdapter(sm)
        
        # Inject mock handlers
        class MockCC:
            def issue_command(self, *args, **kwargs): pass
            
        sh = StateHandler(adapter, sm)
        adapter.set_dependencies(sh, MockCC())
        
        print("PASS: BMOAdapter instantiated")
    except Exception as e:
        print(f"FAIL: Adapter instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Check registered state data
    print("Checking registered BMO state data...")
    active_data = StateRegistry.get_state_data(StateRegistry.ACTIVE)
    
    # BMO Active Data expected: [0, 0.1, 0, 0.2, 0.2]
    expected = [0, 0.1, 0, 0.2, 0.2]
    
    if active_data:
        print(f"INFO: Data found: {active_data}")
        if active_data == expected:
             print("PASS: BMO Active data matches expected values.")
        else:
             print(f"FAIL: BMO Active data mismatch. Expected {expected}, Got {active_data}")
    else:
        print("FAIL: ACTIVE state data NOT found after adapter init")

    # 3. Test Render
    print("Testing BMO Render...")
    try:
        surf = pygame.Surface((800, 480))
        adapter.render(surf, 0)
        print("PASS: BMO Render ran without error")
    except Exception as e:
        print(f"FAIL: BMO Render failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bmo_registry()
