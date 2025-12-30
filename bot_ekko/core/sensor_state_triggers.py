import pygame
from bot_ekko.modules.data_models import SensorData
from bot_ekko.modules.sensor_fusion.sensor_triggers import SensorDataTriggers
from bot_ekko.config import SENSOR_TRIGGER_ENTRY_TIME, SENSOR_TRIGGER_EXIT_TIME
from bot_ekko.core.logger import get_logger

logger = get_logger("SensorStateTrigger")


class SensorStateTrigger:
    def __init__(self, state_handler):
        self.state_handler = state_handler
        self.triggers = SensorDataTriggers()
    
    def wait_sensor_trigger(self, duration: int):  # todo: this is buggy rn, if sensor is True till the duration, it will not wait at all
        return pygame.time.get_ticks() - self.state_handler.state_entry_time > duration
    
    def trigger_states(self, sensor_data: SensorData):
        is_proximity = self.triggers.check_proximity(sensor_data)
        is_distance = self.triggers.check_distance(sensor_data)

        if is_proximity:
            if not self.state_handler.interrupt_state:
                if self.wait_sensor_trigger(SENSOR_TRIGGER_ENTRY_TIME):
                    self.state_handler.state_machine.store_context()
                    self.state_handler.interrupt_state = True
                    self.state_handler.set_state("ANGRY")
                    logger.info("Triggering RAINBOW_EYES state from proximity")
            # If already interrupted, stay in state (do nothing)
            
        elif is_distance:
            if not self.state_handler.interrupt_state:
                if self.wait_sensor_trigger(SENSOR_TRIGGER_ENTRY_TIME):
                    self.state_handler.state_machine.store_context()
                    self.state_handler.interrupt_state = True
                    self.state_handler.set_state("DISTANCE")
                    logger.info("Triggering DISTANCE state from distance")
            # If already interrupted, stay in state (do nothing)

        else:
            # No active triggers, check for exit
            if self.state_handler.interrupt_state and self.wait_sensor_trigger(SENSOR_TRIGGER_EXIT_TIME):
                self.state_handler.state_machine.restore_context()
                self.state_handler.interrupt_state = False
                logger.info("Restoring context from interrupt state")
                self.state_handler.state_entry_time = 0