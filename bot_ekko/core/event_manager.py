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
        interrupt_manager: InterruptManager,
        gif_api = None,
        chat_api = None,
    ):
        self.sensor_data_trigger = sensor_data_trigger
        self.command_center = command_center
        self.state_renderer = state_renderer
        self.state_handler = state_handler
        self.interrupt_manager = interrupt_manager
        self.gif_api = gif_api
        self.chat_api = chat_api

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
                self.interrupt_manager.set_interrupt(self.sensor_interrupt, 50, "WINK")
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
                parts = clean_bt_data.split(";")
                cmd = parts[0]
                param = parts[1] if len(parts) > 1 else None
                
                if cmd == "STATE" and param:
                    self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": param})
                elif cmd == "GIF" and param:
                    if self.gif_api:
                        self.gif_api.fetch_random_gif(param)
                    else:
                        logger.warning("GIF API not initialized")
                elif cmd == "CHAT" and param:
                    if self.chat_api:
                        raw_text = bt_data.text.strip()
                        raw_parts = raw_text.split(";")
                        raw_param = raw_parts[1] if len(raw_parts) > 1 else ""

                        # 1. Switch to CHAT state immediately with LOADING status
                        logger.info(f"Switching to CHAT state (Loading) for query: {raw_param}")
                        self.command_center.issue_command(CommandNames.CHANGE_STATE, params={
                            "target_state": "CHAT", 
                            "is_loading": True,
                            "text": "",
                            "save_history": True
                        })

                        # 2. Define callback to handle response later
                        def on_response(response_text, is_error=False):
                            logger.info(f"Received Chat API response: {response_text} (Error: {is_error})")
                            
                            if is_error:
                                # Revert to ACTIVE state to clear the "Thinking..." screen
                                self.command_center.issue_command(CommandNames.CHANGE_STATE, params={"target_state": "ACTIVE"})
                                
                                # Show error message temporarily using interrupt (5 seconds)
                                self.interrupt_manager.set_interrupt(
                                    "chat_error", 
                                    90, 
                                    "CANVAS", 
                                    params={"param": {"text": response_text}, "interrupt_name": "chat_error"},
                                    duration=5000 
                                )
                            else:
                                # Update CHAT state with text and remove loading
                                self.command_center.issue_command(CommandNames.CHANGE_STATE, params={
                                    "target_state": "CHAT",
                                    "is_loading": False,
                                    "text": response_text
                                })

                        # 3. Call API
                        self.chat_api.query(raw_param, on_response)
                        
                    else:
                        logger.warning("Chat API not initialized")
                elif cmd:
                    self.interrupt_manager.set_interrupt("canvas_media", 80, "CANVAS", params={"param": {"text": param}, "interrupt_name": "canvas_media"})
                    
        
        

        

