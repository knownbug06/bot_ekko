import threading
import time
import serial
import json

from bot_ekko.modules.data_models import SensorData, TOFSensorData, IMUSensorData


class ReadSensorSerialData(threading.Thread):
    def __init__(self, command_queue, port='/dev/ttyUSB0', baud=115200):
        super().__init__(daemon=True)
        self.command_queue = command_queue
        self.running = True
        
        # Initialize Serial
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.ser.setDTR(True) # Toggle DTR to wake up the ESP32
            self.ser.setRTS(True) # Toggle RTS
            self.ser.flush()
            print(f"Connected and reset signals sent to {port}")
        except Exception as e:
            print(f"Serial Connection Error: {e}")
            self.ser = None

        # Our local storage for the latest "state" of the bot
        self.raw_sensor_data = {}
        self.sensor_data = SensorData(
            tof=TOFSensorData(mm=0, status="NA"),
            imu=IMUSensorData(ax=0, ay=0, az=0, status="NA")
        )
    
    def get_sensor_data(self):
        return self.sensor_data

    def run(self):
        """
        sensor data example:
            {"sensor_vlox":{"data":{"mm":170,"status":"ok"}},"sensor_imu":{"data":{"ax":0,"ay":0,"az":0,"status":"NA"}}}
        """
        if not self.ser:
            print("Sensor Service failed to start: No Serial device.")
            return

        print("Sensor Service Started")
        while self.running:
            if self.ser.in_waiting > 0:
                try:
                    # 1. Read the JSON line from ESP32
                    line = self.ser.readline().decode('utf-8').strip()
                    raw_json = json.loads(line)
                    self.raw_sensor_data = raw_json
                    vlox_sensor_data = raw_json['sensor_vlox']['data']
                    imu_sensor_data = raw_json['sensor_imu']['data']
                    
                    self.sensor_data = SensorData(
                        tof=TOFSensorData(
                            mm=vlox_sensor_data['mm'],
                            status=vlox_sensor_data['status']
                        ),
                        imu=IMUSensorData(
                            ax=imu_sensor_data['ax'],
                            ay=imu_sensor_data['ay'],
                            az=imu_sensor_data['az'],
                            status=imu_sensor_data['status']
                        )
                    )

                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Skip partial lines or serial noise
                    continue
                except Exception as e:
                    print(f"Sensor Loop Error: {e}")

            time.sleep(0.01) # High frequency but gives CPU breathing room

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()