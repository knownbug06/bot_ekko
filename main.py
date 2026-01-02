import pygame
import sys
import signal
import queue
import random
from bot_ekko.core.state_machine import StateHandler
from bot_ekko.modules.media_interface import MediaModule
from bot_ekko.modules.sensor_fusion.sensor_data_reader import ReadSensorSerialData
from bot_ekko.modules.comms.comms_bluetooth import BluetoothManager

from bot_ekko.core.state_machine import StateMachine
from bot_ekko.core.eyes import Eyes
from bot_ekko.sys_config import *
from bot_ekko.core.logger import get_logger
from bot_ekko.core.display_manager import init_display
from bot_ekko.core.command_center import CommandCenter
from bot_ekko.core.state_renderer import StateRenderer
from bot_ekko.core.command_center import Command
from bot_ekko.core.event_manager import EventManager
from bot_ekko.modules.sensor_fusion.sensor_triggers import SensorDataTriggers
from bot_ekko.core.interrupt_manager import InterruptManager


logger = get_logger("Main")



def handle_sigterm(signum, frame):
    raise KeyboardInterrupt

def main():
    logger.info("Starting Bot Ekko...")

    screen, logical_surface = init_display((PHYSICAL_W, PHYSICAL_H), (LOGICAL_W, LOGICAL_H), fullscreen=True)
    pygame.mouse.set_visible(False)
    
    clock = pygame.time.Clock()

    # 1. Thread-safe command queue
    cmd_queue: queue.Queue[Command] = queue.Queue()

    # 2. Initialize Architecture
    state_machine = StateMachine()
    eyes = Eyes(state_machine)
    state_handler = StateHandler(eyes, state_machine)
    command_center = CommandCenter(cmd_queue, state_handler)
    interrupt_manager = InterruptManager(state_handler, command_center)
    state_renderer = StateRenderer(eyes, state_handler, command_center, interrupt_manager)
    
    
    # sensor reader
    sensor_reader = ReadSensorSerialData(cmd_queue)
    sensor_reader.start()
    
    
    sensor_data_triggers = SensorDataTriggers()
    event_manager = EventManager(sensor_data_triggers, command_center, state_renderer, state_handler, interrupt_manager)    
    

    # bluetooth manager
    bluetooth_manager = BluetoothManager()
    bluetooth_manager.start()


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

                eyes.apply_physics()

                sensor_data = sensor_reader.get_sensor_data()
                bluetooth_data = bluetooth_manager.get_bt_data()

                logger.debug(f"TOF Distance: {sensor_data.tof.mm}")
                logger.debug(f"Bluetooth Data: {bluetooth_data}")

                event_manager.update_sensor_events(sensor_data)
                event_manager.update_bt_events(bluetooth_data)

                # Render
                if pygame.display.get_init():
                    # Pump events internally to keep window responsive (even if we ignore them)
                    pygame.event.pump()
                    logical_surface.fill(BLACK)
                    state_renderer.render(logical_surface, now)
                    
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
