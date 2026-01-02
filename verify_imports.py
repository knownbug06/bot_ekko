try:
    import main
    from bot_ekko.core.event_manager import EventManager
    from bot_ekko.core.command_center import CommandCenter
    from bot_ekko.core.interrupt_manager import InterruptManager
    from bot_ekko.core.state_renderer import StateRenderer
    from bot_ekko.core.state_machine import StateHandler
    print("Imports successful")
except ImportError as e:
    print(f"Import failed: {e}")
    exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)
