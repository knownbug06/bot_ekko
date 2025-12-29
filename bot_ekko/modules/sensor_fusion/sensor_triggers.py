from bot_ekko.modules.data_models import SensorData


class SensorDataTriggers:
    def __init__(self):
        self.triggers = {
            "TOF": {
                "proximity": 50,
                "distance": 500
            },
            "TILT": {
                "x": 10,
                "y": 10
            }
        }
    
    def check_proximity(self, sensor_data: SensorData):
        if not sensor_data.tof.status == "ok":
            return False
        if sensor_data.tof.mm < self.triggers["TOF"]["proximity"]:
            return True
        return False
    
    def check_distance(self, sensor_data: SensorData):
        # if not sensor_data.tof.status == "ok":
        #     return False
        # if sensor_data.tof.mm < self.triggers["TOF"]["distance"]:
        #     return True
        return False