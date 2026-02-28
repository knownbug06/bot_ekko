import pygame
import sys
import signal
import queue
from dotenv import load_dotenv

load_dotenv()

from bot_ekko.sys_config import PHYSICAL_W, PHYSICAL_H, LOGICAL_W, LOGICAL_H, BLACK, SYSTEM_MONITORING_ENABLED
from bot_ekko.core.logger import get_logger

# Core Components
from bot_ekko.core.state_machine import StateHandler, StateMachine
from bot_ekko.core.display_manager import DisplayManager
from bot_ekko.core.command_center import CommandCenter, Command
from bot_ekko.utils import load_class_from_path

# Modules
from bot_ekko.sys_config import SCREEN_ROTATION

from bot_ekko.core.mainbot import MainBotServicesManager
from bot_ekko.core.models import SystemConfig
from bot_ekko.core.interrupts import InterruptHandler
import json


logger = get_logger("Main")



def handle_sigterm(signum, frame):
    raise KeyboardInterrupt

def main():
    logger.info("Starting Bot Ekko...")

    display_manager = DisplayManager((PHYSICAL_W, PHYSICAL_H), (LOGICAL_W, LOGICAL_H), fullscreen=True)
    screen, logical_surface = display_manager.init_display()
    pygame.mouse.set_visible(False)
    
    clock = pygame.time.Clock()

    # 1. Thread-safe command queue
    cmd_queue: queue.Queue[Command] = queue.Queue()
    
    # Load System Config
    try:
        system_config = SystemConfig.from_json_file("bot_ekko/config.json")
    except Exception as e:
        logger.critical(f"Failed to load system config: {e}")
        sys.exit(1)
        
    ui_config = system_config.ui_expression_config
    adapter_module = ui_config.adapter_module_path
    adapter_class = ui_config.adapter_class_name


    # 2. Initialize Architecture
    state_machine = StateMachine()
    
    # Render Engine (Dynamic Loading)
    try:
        RenderEngineClass = load_class_from_path(adapter_module, adapter_class)
        render_engine = RenderEngineClass(state_machine)
    except Exception as e:
        logger.critical(f"Failed to load render engine: {e}")
        sys.exit(1)
    
    # Create StateHandler with render_engine
    state_handler = StateHandler(render_engine, state_machine)
    
    # Command Center
    command_center = CommandCenter(cmd_queue, state_handler)
    
    # Post-Init Injection for Render Engine
    render_engine.set_dependencies(state_handler, command_center, system_config)

    interrupt_handler = InterruptHandler(command_center, state_handler)

    mainbot = MainBotServicesManager(cmd_queue, interrupt_handler, state_handler)
    mainbot.init_services(system_config.services)
    mainbot.start_services()

    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        while True:
            try:
                now = pygame.time.get_ticks()

                # Process Command Queue
                while not cmd_queue.empty():
                    try:
                        command = cmd_queue.get_nowait()
                        logger.debug(f"Processing command: {command}")
                        command.execute()
                    except queue.Empty:
                        pass

                mainbot.service_loop_update()
                interrupt_handler.update()

                render_engine.update(now)

                # Render
                if pygame.display.get_init():
                    # Pump events internally to keep window responsive (even if we ignore them)
                    pygame.event.pump()
                    logical_surface.fill(BLACK)
                    render_engine.render(logical_surface, now)
                    
                    # Transform and Display
                    rotated = pygame.transform.rotate(logical_surface, SCREEN_ROTATION)
                    screen.blit(rotated, (0, 0))
                    pygame.display.flip()
                else:
                    print('no display')
                clock.tick(60)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                raise
    except KeyboardInterrupt:
        logger.info("\nStopping bot...")
    finally:
        logger.info("Cleaning up resources...")
        mainbot.stop_services()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
