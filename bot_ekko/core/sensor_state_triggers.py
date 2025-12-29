import pygame
from bot_ekko.modules.data_models import SensorData
from bot_ekko.modules.sensor_fusion.sensor_triggers import SensorDataTriggers


class SensorStateTrigger:
    def __init__(self, state_handler):
        self.state_handler = state_handler
        self.triggers = SensorDataTriggers()
    
    def trigger_states(self, sensor_data: SensorData):
        if self.triggers.check_proximity(sensor_data):
            self.state_handler.state_machine.store_context()
            self.state_handler.interrupt_state = True
            self.state_handler.set_state("SCARED")
        elif self.triggers.check_distance(sensor_data):
            self.state_handler.state_machine.store_context()
            self.state_handler.interrupt_state = True
            self.state_handler.set_state("DISTANCE")
        else:
            if self.state_handler.interrupt_state:
                # Minimum duration check (2 seconds)
                if pygame.time.get_ticks() - self.state_handler.state_entry_time > 5000:
                    self.state_handler.state_machine.restore_context()
                    self.state_handler.interrupt_state = False