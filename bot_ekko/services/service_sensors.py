import json
import serial
import time
from typing import Optional, Dict, Union, Any

from bot_ekko.core.base import ThreadedService, ServiceStatus
from bot_ekko.core.errors import SensorConnectionError
from bot_ekko.core.models import SensorData, TOFSensorData, IMUSensorData, ServiceSensorConfig
from bot_ekko.core.command_center import CommandCenter
from bot_ekko.core.interrupts import InterruptHandler
from bot_ekko.core.logger import get_logger


class SensorTriggers:
    """
    Evaluates sensor data against configured thresholds to determine triggers.
    """
    def __init__(self, sensor_triggers: Dict[str, Union[str, Dict[str, int]]]) -> None:
        self.triggers = sensor_triggers
        self.logger = get_logger("SensorTriggers")

    def check_proximity(self, sensor_data: SensorData) -> bool:
        """
        Check if the proximity sensor values trigger a reaction.
        
        Args:
            sensor_data (SensorData): The latest sensor readings.
            
        Returns:
            bool: True if proximity trigger condition is met.
        """
        if "TOF" not in self.triggers:
            self.logger.warning("TOF triggers not configured, proximity check will always return fail.")
            return False
        
        # Determine trigger threshold
        # Assuming format: {"TOF": {"proximity": 200}}
        trigger_config = self.triggers["TOF"]
        if isinstance(trigger_config, dict):
            threshold = trigger_config.get("proximity", 150)
        else:
            threshold = 150 # Default safe fallback

        if not sensor_data.tof.status == "ok":
            return False
        
        if sensor_data.tof.mm < threshold:
            return True
        return False


class SensorService(ThreadedService):
    """
    Service to interface with external hardware sensors via Serial (e.g. ESP32).
    """
    def __init__(self, command_center: CommandCenter, service_sensor_config: ServiceSensorConfig, interrupt_handler: InterruptHandler) -> None:
        """
        Initialize the Sensor Service.

        Args:
            command_center (CommandCenter): For issuing downstream commands (unused currently but passed).
            service_sensor_config (ServiceSensorConfig): Configuration.
            interrupt_handler (InterruptHandler): For triggering immediate state interrupts.
        """
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
        Main service loop. Reads JSON lines from serial.
        """
        if not self.ser:
            self.logger.error("Sensor Service running without active serial connection.")
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
        """Stops the service and closes serial port."""
        super().stop()
        if self.ser:
            try:
                self.ser.close()
                self.logger.info("Serial port closed")
            except Exception as e:
                self.logger.error(f"Error closing serial port: {e}")
    
    def update(self) -> None:
        """Checks sensor triggers and interrupts if needed."""
        sensor_data = self.get_sensor_data()
        self.logger.debug(f"Sensor Data: {sensor_data}")
        
        is_proximity_triggered = self.sensor_triggers.check_proximity(sensor_data)
        
        if is_proximity_triggered:
            self.interrupt_handler.set_interrupt(
                name="proximity",
                duration=self.service_sensor_config.proximity_duration,
                target_state="ANGRY",
                priority=10,
                params={}
            )

