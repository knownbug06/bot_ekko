import pygame
import sys
import signal
import queue
import signal
import queue
import os
from dotenv import load_dotenv

load_dotenv()

import random

from bot_ekko.sys_config import PHYSICAL_W, PHYSICAL_H, LOGICAL_W, LOGICAL_H, BLACK, SYSTEM_MONITORING_ENABLED
from bot_ekko.core.logger import get_logger

# Core Components
from bot_ekko.core.state_machine import StateHandler, StateMachine
from bot_ekko.core.eyes import Eyes
from bot_ekko.core.display_manager import init_display
from bot_ekko.core.command_center import CommandCenter, Command
from bot_ekko.core.state_renderer import StateRenderer
from bot_ekko.core.event_manager import EventManager
from bot_ekko.core.interrupt_manager import InterruptManager

# Modules
from bot_ekko.modules.media_interface import MediaModule
from bot_ekko.modules.sensor_fusion.sensor_data_reader import ReadSensorSerialData
from bot_ekko.modules.sensor_fusion.sensor_triggers import SensorDataTriggers
from bot_ekko.modules.comms.comms_bluetooth import BluetoothManager
from bot_ekko.modules.system_logs import SystemMonitor
from bot_ekko.apis.adapters.tenor_api import TenorAPI
from bot_ekko.apis.adapters.chat_api import ChatAPI
from bot_ekko.sys_config import SCREEN_ROTATION, SERVER_CONFIG

from bot_ekko.core.mainbot import MainBotServicesManager
from bot_ekko.core.models import ServicesConfig
from bot_ekko.core.interrupts import InterruptHandler


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

    services_config = ServicesConfig.from_json_file("bot_ekko/config.json")

    # 2. Initialize Architecture
    state_machine = StateMachine()
    eyes = Eyes(state_machine)
    state_handler = StateHandler(eyes, state_machine)
    command_center = CommandCenter(cmd_queue, state_handler)
    interrupt_manager = InterruptManager(state_handler, command_center)
    state_renderer = StateRenderer(eyes, state_handler, command_center, interrupt_manager)

    interrupt_handler = InterruptHandler(command_center, state_handler)

    mainbot = MainBotServicesManager(cmd_queue, interrupt_handler, state_handler)
    # breakpoint()
    mainbot.init_services(services_config)
    mainbot.start_services()
    
    
    
    # sensor reader
    # sensor_reader = ReadSensorSerialData(cmd_queue)
    # sensor_reader.start()
    
    
    # API Adapters
    # TENOR_API_KEY = os.getenv("TENOR_API_KEY") 
    # gif_api = TenorAPI(command_center, TENOR_API_KEY)
    
    # chat_api = ChatAPI(command_center, SERVER_CONFIG["url"])

    # sensor_data_triggers = SensorDataTriggers()
    # event_manager = EventManager(sensor_data_triggers, command_center, state_renderer, state_handler, interrupt_manager, gif_api, chat_api)    
    

    # bluetooth manager
    # bluetooth_manager = BluetoothManager()
    # bluetooth_manager.start()

    # System Monitor
    system_monitor = None
    if SYSTEM_MONITORING_ENABLED:
        system_monitor = SystemMonitor()
        system_monitor.start()


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

                eyes.apply_physics()


                # sensor_data = sensor_reader.get_sensor_data()
                # bluetooth_data = bluetooth_manager.get_bt_data()

                # logger.debug(f"TOF Distance: {sensor_data.tof.mm}")
                # logger.debug(f"Bluetooth Data: {bluetooth_data}")

                # event_manager.update_sensor_events(sensor_data)
                # event_manager.update_bt_events(bluetooth_data)

                # Render
                if pygame.display.get_init():
                    # Pump events internally to keep window responsive (even if we ignore them)
                    pygame.event.pump()
                    logical_surface.fill(BLACK)
                    state_renderer.render(logical_surface, now)
                    
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
        # sensor_reader.stop()
        # bluetooth_manager.stop()
        if system_monitor:
            system_monitor.stop()
        if gif_api:
            gif_api.stop()
        if chat_api:
            chat_api.stop()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
