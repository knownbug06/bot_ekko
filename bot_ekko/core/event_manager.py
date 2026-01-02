from bot_ekko.core.command_center import CommandCenter
from bot_ekko.core.state_renderer import StateRenderer
from bot_ekko.core.state_machine import StateHandler
from bot_ekko.core.interrupt_manager import InterruptManager
from bot_ekko.core.logger import get_logger
from bot_ekko.sys_config import SENSOR_TRIGGER_ENTRY_TIME, SENSOR_TRIGGER_EXIT_TIME
from bot_ekko.modules.sensor_fusion.sensor_data_reader import SensorData
from bot_ekko.modules.sensor_fusion.sensor_triggers import SensorDataTriggers
from bot_ekko.core.command_center import CommandNames
from bot_ekko.core.models import BluetoothData
import pygame

logger = get_logger("EventManager")

class EventManager:
    def __init__(
        self, sensor_data_trigger: SensorDataTriggers,
        command_center: CommandCenter,
        state_renderer: StateRenderer,
        state_handler: StateHandler,
        interrupt_manager: InterruptManager
    ):
        self.sensor_data_trigger = sensor_data_trigger
        self.command_center = command_center
        self.state_renderer = state_renderer
        self.state_handler = state_handler
        self.interrupt_manager = interrupt_manager

        self.sensor_interrupt = "sensor_interrupt"

    def wait_sensor_trigger(self, duration: int):
        return pygame.time.get_ticks() - self.state_handler.state_entry_time > duration
    
    def update_sensor_events(self, sensor_data: SensorData):
        """
        Evaluates sensor data and triggers state changes if thresholds are met.
        
        Args:
            sensor_data (SensorData): The latest data packet from the sensors.
        """
        is_proximity = self.sensor_data_trigger.check_proximity(sensor_data)
        is_distance = self.sensor_data_trigger.check_distance(sensor_data)

        if is_proximity:
            if self.wait_sensor_trigger(SENSOR_TRIGGER_ENTRY_TIME):
                self.interrupt_manager.set_interrupt(self.sensor_interrupt, 50, "UWU")
                logger.debug("Set proximity interrupt")
            
        elif is_distance:
            if self.wait_sensor_trigger(SENSOR_TRIGGER_ENTRY_TIME):
                self.interrupt_manager.set_interrupt(self.sensor_interrupt, 30, "DISTANCE")
                logger.debug("Set distance interrupt")

        else:
            self.interrupt_manager.clear_interrupt(self.sensor_interrupt)
    
    def update_bt_events(self, bt_data: BluetoothData):
        if bt_data:
            if bt_data.is_connected:
                clean_bt_data = bt_data.text.strip().upper()
                cmd, param, *_ = clean_bt_data.split(";") + [None, None] 
                
                if cmd == "STATE":
                    self.command_center.issue_command(CommandNames.CHANGE_STATE, {"target_state": param})
                else:
                    self.interrupt_manager.set_interrupt("canvas_media", 80, "CANVAS", {"param": {"text": param}, "interrupt_name": "canvas_media"})
                    
        
        

        

