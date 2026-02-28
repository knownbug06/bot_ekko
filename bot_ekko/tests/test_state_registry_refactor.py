import sys
import os

# dynamic path setup - ensure we can import bot_ekko
# Current file: .../bot_ekko/bot_ekko/tests/test_registry.py
# Root of package: .../bot_ekko/bot_ekko

current_dir = os.path.dirname(os.path.abspath(__file__))
# bot_ekko/bot_ekko
package_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(package_root)

# Now we can import bot_ekko (as top level package if run from outside)
# OR if run from inside, we need to handle it.
# Usually we run `python -m bot_ekko.tests.test_registry` or similar.
# But let's try direct path manipulation to simulate installed package or local dev.

if package_root not in sys.path:
    sys.path.insert(0, package_root)

try:
    from bot_ekko.core.state_registry import StateRegistry
    from bot_ekko.ui_expressions_lib.eyes.adapter import EyesExpressionAdapter
    from bot_ekko.core.state_machine import StateMachine
except ImportError:
    # Try appending just the parent
    parent = os.path.dirname(current_dir)
    sys.path.insert(0, os.path.dirname(parent))
    from bot_ekko.core.state_registry import StateRegistry
    from bot_ekko.ui_expressions_lib.eyes.adapter import EyesExpressionAdapter
    from bot_ekko.core.state_machine import StateMachine

def test_registry():
    print("Testing StateRegistry Refactor...")
    
    # 1. Check initial state
    print("Checking initial state of StateRegistry...")
    try:
        data = StateRegistry.get_state_data(StateRegistry.ACTIVE)
        if data is None:
            print("PASS: ACTIVE state is initially None")
        else:
            print(f"FAIL: ACTIVE state is not None: {data}")
    except Exception as e:
        # If adapter was imported at top level, it might have already run its code?
        # No, adapter class defined but not instantiated usually doesn't run registry code unless it's at module level.
        # In adapter.py, I put the registration in __init__. So it should be fine.
        print(f"Error checking initial state: {e}")
        
    # 2. Instantiate Adapter (which should register states)
    print("Instantiating EyesExpressionAdapter...")
    try:
        sm = StateMachine()
        adapter = EyesExpressionAdapter(sm)
        print("PASS: Adapter instantiated")
    except Exception as e:
        print(f"FAIL: Adapter instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Check registered state data
    print("Checking registered state data...")
    active_data = StateRegistry.get_state_data(StateRegistry.ACTIVE)
    if active_data:
        print(f"PASS: ACTIVE state data found: {active_data}")
        # Validate format: [Base_Height, Gaze_Speed, Radius, Close_Spd, Open_Spd]
        if isinstance(active_data, list) and len(active_data) == 5:
             print("PASS: ACTIVE state data format correct")
        else:
             print(f"FAIL: ACTIVE state data format incorrect: {active_data}")
    else:
        print("FAIL: ACTIVE state data NOT found after adapter init")

    # 4. Test Physics (uses registry)
    print("Testing Physics with Registry...")
    try:
        adapter.eyes.apply_physics()
        print("PASS: Physics apply_physics() ran without error")
    except Exception as e:
        print(f"FAIL: Physics apply_physics() failed: {e}")
        import traceback
        traceback.print_exc()

    # 5. Test Expressions (uses registry)
    print("Testing Expressions with Registry...")
    try:
        # Mock surface
        import pygame
        # pygame.init() # Headless might fail visual init but surface creation usually works
        surf = pygame.Surface((800, 480))
        adapter.expressions.draw_generic(surf)
        print("PASS: Expressions draw_generic() ran without error")
    except Exception as e:
        print(f"FAIL: Expressions draw_generic() failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_registry()
