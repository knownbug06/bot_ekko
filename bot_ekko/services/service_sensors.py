import json
import serial
import time
from typing import Optional

from bot_ekko.core.base import ThreadedService, ServiceStatus
from bot_ekko.core.errors import SensorConnectionError
from bot_ekko.core.models import SensorData, TOFSensorData, IMUSensorData
from bot_ekko.core.command_center import CommandCenter
from bot_ekko.core.interrupts import InterruptHandler
from bot_ekko.core.models import ServiceSensorConfig
from typing import Dict, Union
from bot_ekko.core.logger import get_logger


class SensorTriggers:
    def __init__(self, sensor_triggers: Dict[str, Union[str, Dict[str, int]]]) -> None:
        self.triggers = sensor_triggers
        self.logger = get_logger("SensorTriggers")

    def check_proximity(self, sensor_data: SensorData):
        if "TOF" not in self.triggers:
            self.logger.warning("TOF triggers not configured, proximity check will always return fail.")
            return False
        
        if not sensor_data.tof.status == "ok":
            return False
        
        if sensor_data.tof.mm < self.triggers["TOF"]["proximity"]:
            return True
        return False


class SensorService(ThreadedService):
    def __init__(self, command_center: CommandCenter, service_sensor_config: ServiceSensorConfig, interrupt_handler: InterruptHandler) -> None:
        super().__init__(service_sensor_config.name, enabled=service_sensor_config.enabled)
        
        self.port = service_sensor_config.port
        self.baud = service_sensor_config.baud
        self.ser: Optional[serial.Serial] = None
        self.service_sensor_config = service_sensor_config

        self.command_center = command_center
        self.interrupt_handler = interrupt_handler

        self.sensor_triggers = SensorTriggers(service_sensor_config.sensor_triggers)
        
        # Initialize empty sensor data
        self.sensor_data = SensorData(
            tof=TOFSensorData(mm=0, status="NA"),
            imu=IMUSensorData(ax=0, ay=0, az=0, status="NA")
        )
        # self.init()

    def init(self) -> None:
        """Initialize serial connection."""
        self.logger.info(f"Initializing serial connection to {self.port} at {self.baud} baud.")
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            self.ser.setDTR(True) # Toggle DTR to wake up the ESP32
            self.ser.setRTS(True) # Toggle RTS
            self.ser.flush()
            self.logger.info(f"Connected and reset signals sent to {self.port}")
            super().init()
        except Exception as e:
            self.logger.error(f"Serial Connection Error: {e}")
            self.update_stat("connection_error", str(e))
            self.ser = None # Ensure it's None if failed
            raise SensorConnectionError(f"Failed to connect to sensor port {self.port}: {e}", self.name) from e

    def _run(self) -> None:
        """
        Main service loop.
        sensor data example:
            {"sensor_vlox":{"data":{"mm":170,"status":"ok"}},"sensor_imu":{"data":{"ax":0,"ay":0,"az":0,"status":"NA"}}}
        """
        if not self.ser:
            self.logger.error("Sensor Service running without active serial connection (Init failed?).")
            # We could return here, or keep running if we support re-connecting during run.
            # For now, let's assume if start() succeeded, init() succeeded. 
            # But if start() auto-called init() and it failed, start() would have raised.
            # So here we should be safe.
            # HOWEVER, if I want to be super robust:
            return

        self.logger.info("Sensor Service Loop Started")
        
        while not self._stop_event.is_set():
            try:
                if self.ser.in_waiting > 0:
                    try:
                        # 1. Read the JSON line from ESP32
                        line = self.ser.readline().decode('utf-8').strip()
                        if not line:
                            continue
                            
                        raw_json = json.loads(line)
                        
                        # Update stats
                        self.increment_stat("messages_received")
                        
                        vlox_sensor_data = raw_json.get('sensor_vlox', {}).get('data', {})
                        imu_sensor_data = raw_json.get('sensor_imu', {}).get('data', {})
                        
                        self.sensor_data = SensorData(
                            tof=TOFSensorData(
                                mm=vlox_sensor_data.get('mm', 0),
                                status=vlox_sensor_data.get('status', "NA")
                            ),
                            imu=IMUSensorData(
                                ax=imu_sensor_data.get('ax', 0),
                                ay=imu_sensor_data.get('ay', 0),
                                az=imu_sensor_data.get('az', 0),
                                status=imu_sensor_data.get('status', "NA")
                            )
                        )

                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Skip partial lines or serial noise
                        self.increment_stat("decode_errors")
                        continue
                    except Exception as e:
                        self.logger.error(f"Sensor Loop Error: {e}")
                        self.increment_stat("processing_errors")
                        self.update_stat("last_error", str(e))
                
                # managing loop frequency
                self._stop_event.wait(self.service_sensor_config.sensor_update_rate)
                
            except Exception as e:
                self.logger.error(f"Critical Loop Error: {e}")
                self.set_status(ServiceStatus.ERROR)
                time.sleep(1) # Prevent tight loop on permanent error

    def get_sensor_data(self) -> SensorData:
        return self.sensor_data

    def stop(self) -> None:
        super().stop()
        if self.ser:
            try:
                self.ser.close()
                self.logger.info("Serial port closed")
            except Exception as e:
                self.logger.error(f"Error closing serial port: {e}")
    
    def update(self) -> None:
        is_proximity_triggered = self.sensor_triggers.check_proximity(self.get_sensor_data())
        # print(self.get_sensor_data().tof.mm)
        if is_proximity_triggered:
            self.interrupt_handler.set_interrupt(
                name="proximity",
                duration=self.service_sensor_config.proximity_duration,
                target_state="ANGRY",
                priority=10,
                params={}
            )
