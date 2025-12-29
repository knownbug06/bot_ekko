import pygame
import sys
import queue
from bot_ekko.core.state_handler import StateHandler
from bot_ekko.modules.media_interface import InterfaceModule
from bot_ekko.modules.sensor_fusion.sensor_data_reader import ReadSensorSerialData
from bot_ekko.core.sensor_state_triggers import SensorStateTrigger
from bot_ekko.core.state_machine import StateMachine
from bot_ekko.core.eyes import Eyes
from bot_ekko.config import *

import random


def main():
    pygame.init()
    
    screen = pygame.display.set_mode((PHYSICAL_W, PHYSICAL_H))
    pygame.mouse.set_visible(False)
    
    logical_surface = pygame.Surface((LOGICAL_W, LOGICAL_H))
    clock = pygame.time.Clock()

    # 1. Thread-safe command queue
    cmd_queue = queue.Queue()

    # 2. Initialize Architecture
    state_machine = StateMachine()
    eyes = Eyes(state_machine)
    state_handler = StateHandler(eyes, state_machine)

    interface = InterfaceModule(state_machine)
    sensor_reader = ReadSensorSerialData(cmd_queue)
    sensor_reader.start()

    sensor_trigger = SensorStateTrigger(state_handler)

    try:
        while True:
            try:
                now = pygame.time.get_ticks()

                # Schedule still runs (but we don't pass surface yet until render phase?)
                # Actually user asked to combine draw and logic. logic runs during render?
                # Or we just run handle_states ONCE inside the render block.
                
                if state_machine.get_state() != "INTERFACE":
                    eyes.apply_physics()

                # Render
                if pygame.display.get_init():
                    # Pump events internally to keep window responsive (even if we ignore them)
                    pygame.event.pump()
                    
                    logical_surface.fill(BLACK)
                    sensor_data = sensor_reader.get_sensor_data()
                    print(sensor_data.tof.mm)
                    sensor_trigger.trigger_states(sensor_data)
                    
                    if state_machine.get_state() == "INTERFACE":
                        interface.draw(logical_surface)
                    else:
                        # Logic AND Drawing happen here now
                        state_handler.handle_states(logical_surface, now, 21, 0, 8, 0)
                    
                    # Transform and Display
                    rotated = pygame.transform.rotate(logical_surface, -90)
                    screen.blit(rotated, (0, 0))
                    pygame.display.flip()
                
                clock.tick(60)
                
            except Exception as e:
                print(f"Main loop error: {e}")
    except KeyboardInterrupt:
        print("\nStopping bot...")
    finally:
        print("Cleaning up resources...")
        sensor_reader.stop()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
