import queue
from typing import Dict

from bot_ekko.core.command_center import Command, CommandCenter
from bot_ekko.services import SensorService, BluetoothService
from bot_ekko.core.models import ServicesConfig
from bot_ekko.core.interrupts import InterruptHandler
from bot_ekko.core.state_machine import StateHandler
from bot_ekko.core.logger import get_logger
from bot_ekko.services.errors import SensorConnectionError

logger = get_logger("MainBotServicesManager")


class MainBotServicesManager:

    def __init__(self, command_queue: queue.Queue[Command], interrupt_handler: InterruptHandler, state_handler: StateHandler):
        self.command_queue = command_queue
        
        # services
        self.service_sensor = None
        self.service_bt = None
        self.state_handler = state_handler

        self.command_center = CommandCenter(self.command_queue, self.state_handler)
        self.interrupt_handler = interrupt_handler

        self.services = []

    def init_services(self, services_config: ServicesConfig):
        try:
            self.service_sensor = SensorService(
                command_center=self.command_center,
                service_sensor_config=services_config.sensor_service,
                interrupt_handler=self.interrupt_handler
            )
            # self.service_bt = BluetoothService(
            #     command_center=self.command_center,
            #     service_bt_config=services_config.bt_service
            # )

            # add services to the dictionary
            self.services.append(self.service_sensor)
            # self.services.append(selfa.service_bt)
        except SensorConnectionError as e:
            logger.error(f"Failed to initialize services: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    def start_services(self):
        for service in self.services:
            logger.info(f"Starting service: {service.name}")
            service.start()
    
    def stop_services(self):
        for service in self.services:
            service.stop()
    
    def service_loop_update(self):
        for service in self.services:
            service.update()
        



