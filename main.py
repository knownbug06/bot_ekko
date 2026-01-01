import pygame
import sys
import signal
import queue
import random
from bot_ekko.core.state_center import StateHandler
from bot_ekko.modules.media_interface import MediaModule
from bot_ekko.modules.sensor_fusion.sensor_data_reader import ReadSensorSerialData
from bot_ekko.modules.comms.comms_bluetooth import BluetoothManager
from bot_ekko.core.sensor_state_triggers import SensorStateTrigger
from bot_ekko.core.state_machine import StateMachine
from bot_ekko.core.eyes import Eyes
from bot_ekko.config import *
from bot_ekko.core.logger import get_logger
from bot_ekko.core.display_manager import init_display

logger = get_logger("Main")



def handle_sigterm(signum, frame):
    raise KeyboardInterrupt

def main():
    logger.info("Starting Bot Ekko...")

    screen, logical_surface = init_display((PHYSICAL_W, PHYSICAL_H), (LOGICAL_W, LOGICAL_H), fullscreen=True)
    pygame.mouse.set_visible(False)
    
    clock = pygame.time.Clock()

    # 1. Thread-safe command queue
    cmd_queue = queue.Queue()

    # 2. Initialize Architecture
    state_machine = StateMachine()
    eyes = Eyes(state_machine)
    state_handler = StateHandler(eyes, state_machine)
    
    media_module = MediaModule(state_handler)
    media_module = MediaModule(state_handler)
    state_handler.media_player = media_module
    media_module.start()
    
    # Inject Command Center
    from bot_ekko.core.command_center import CommandCenter
    command_center = CommandCenter(cmd_queue, state_handler)
    state_handler.command_center = command_center
    
    sensor_reader = ReadSensorSerialData(cmd_queue)
    sensor_reader.start()

    bluetooth_manager = BluetoothManager(cmd_queue)
    bluetooth_manager.start()

    sensor_trigger = SensorStateTrigger(state_handler)

    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        while True:
            try:
                now = pygame.time.get_ticks()

                if state_machine.get_state() != "INTERFACE":
                    eyes.apply_physics()

                # Process Command Queue
                while not cmd_queue.empty():
                    try:
                        cmd_raw = cmd_queue.get_nowait().strip()
                        parts = cmd_raw.split(";")
                        cmd = parts[0].upper()
                        
                        params = None
                        if len(parts) > 1:
                             params = {'text': parts[1].strip()}
                        
                        logger.info(f"Processing command: {cmd} with params: {params}")
                        if cmd in STATES:
                            state_handler.set_state(cmd, params)
                        else:
                            logger.warning(f"Invalid command: {cmd}")
                    except queue.Empty:
                        pass

                # Render
                if pygame.display.get_init():
                    # Pump events internally to keep window responsive (even if we ignore them)
                    pygame.event.pump()
                    
                    logical_surface.fill(BLACK)
                    sensor_data = sensor_reader.get_sensor_data()
                    sensor_trigger.trigger_states(sensor_data)
                    logger.debug(f"TOF Distance: {sensor_data.tof.mm}")
                    
                    if state_machine.get_state() == "INTERFACE":
                        # Legacy/Placeholder if INTERFACE state still exists without MediaModule usage
                        pass
                    else:
                        # Logic AND Drawing happen here now
                        state_handler.handle_states(logical_surface, now, *SLEEP_AT, *WAKE_AT)
                    
                    # Transform and Display
                    rotated = pygame.transform.rotate(logical_surface, -90)
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
        sensor_reader.stop()
        bluetooth_manager.stop()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
