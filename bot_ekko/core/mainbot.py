import queue

from bot_ekko.core.command_center import Command, CommandCenter
from bot_ekko.services import SensorService, BluetoothService, GestureService, SystemLogsService
from bot_ekko.core.models import ServicesConfig


from bot_ekko.core.interrupts import InterruptHandler
from bot_ekko.core.state_machine import StateHandler
from bot_ekko.core.logger import get_logger
from bot_ekko.core.errors import SensorConnectionError
from bot_ekko.core.base import ServiceStatus


logger = get_logger("MainBotServicesManager")


class MainBotServicesManager:

    def __init__(self, command_queue: queue.Queue[Command], interrupt_handler: InterruptHandler, state_handler: StateHandler):
        self.command_queue = command_queue

        # services
        self.service_sensor = None
        self.service_bt = None
        self.service_system_logs = None
        self.state_handler = state_handler
        self.service_gesture = None

        self.command_center = CommandCenter(self.command_queue, self.state_handler)
        self.interrupt_handler = interrupt_handler

        self.all_services = []
        self.enabled_services = []

    def init_services(self, services_config: ServicesConfig):
        self.service_sensor = SensorService(
            command_center=self.command_center,
            service_sensor_config=services_config.sensor_service,
            interrupt_handler=self.interrupt_handler
        )
        self.service_bt = BluetoothService(
            command_center=self.command_center,
            service_bt_config=services_config.bt_service
        )
        self.service_gesture = GestureService(
            command_center=self.command_center,
            service_gesture_config=services_config.gesture_service
        )

        self.service_system_logs = SystemLogsService(
            service_config=services_config.system_logs_service
        )

        # add services to the dictionary
        self.all_services.append(self.service_sensor)
        self.all_services.append(self.service_bt)
        self.all_services.append(self.service_gesture)
        self.all_services.append(self.service_system_logs)
        
        # add enabled services to the list
        self.enabled_services = [i for i in self.all_services if i.enabled]
    
    def start_services(self):
        for service in self.enabled_services:
            if service.status == ServiceStatus.RUNNING:
                logger.info(f"Service {service.name} is already running")
                continue
            
            logger.info(f"Starting service: {service.name}")
            try:
                service.start()
            except SensorConnectionError as e:
                logger.error(f"Failed to start service: {service.name}: {e}")
            except Exception as e:
                logger.error(f"Failed to start service: {service.name}: {e}")
                raise
    
    def stop_services(self):
        for service in self.enabled_services:
            if service.status == ServiceStatus.RUNNING:
                logger.info(f"Stopping service: {service.name}...")
                service.stop()
    
    def service_loop_update(self):
        for service in self.enabled_services:
            if service.status == ServiceStatus.RUNNING:
                service.update()
            else:
                logger.debug(f"Service {service.name} is not running, will not update. status: {service.status}")
        
