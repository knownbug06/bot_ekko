import queue
from typing import Dict

from bot_ekko.core.command_center import Command, CommandCenter
from bot_ekko.services import SensorService, BluetoothService
from bot_ekko.core.models import ServicesConfig
from bot_ekko.core.interrupts import InterruptHandler


class MainBotServicesManager:

    def __init__(self, command_queue: queue.Queue[Command], interrupt_handler: InterruptHandler):
        self.command_queue = command_queue
        
        # services
        self.service_sensor = None
        self.service_bt = None

        self.command_center = CommandCenter(self.command_queue)
        self.interrupt_handler = interrupt_handler
        self.services = {}

    def init_services(self, services_config: ServicesConfig):
        try:
            self.service_sensor = SensorService(
                command_center=self.command_center,
                service_sensor_config=services_config.sensor_service
            )
            self.service_bt = BluetoothService(
                command_center=self.command_center,
                service_bt_config=services_config.bt_service
            )

            # add services to the dictionary
            self.services[self.service_sensor.name] = self.service_sensor
            self.services[self.service_bt.name] = self.service_bt
        except Exception as e:
            pass
    
    def start_services(self):
        for service in self.services.values():
            service.start()
    
    def stop_services(self):
        for service in self.services.values():
            service.stop()
    
    def get_service(self, service_name: str):
        return self.services.get(service_name, None)
    
    def service_loop_update(self):
        for service in self.services.values():
            service.update()
        



