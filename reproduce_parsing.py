
import json
from dataclasses import dataclass
from typing import Optional

# Mock classes to match bot_ekko.core.models
@dataclass
class TOFSensorData:
    mm: int
    status: str

@dataclass
class IMUSensorData:
    ax: float
    ay: float
    az: float
    status: str

@dataclass
class SensorData:
    tof: TOFSensorData
    imu: IMUSensorData

def parse_line(line: str) -> Optional[SensorData]:
    try:
        raw_json = json.loads(line)
        vlox_sensor_data = raw_json.get('sensor_vlox', {}).get('data', {})
        imu_sensor_data = raw_json.get('sensor_imu', {}).get('data', {})
        
        sensor_data = SensorData(
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
        return sensor_data
    except Exception as e:
        print(f"Error parsing: {e}")
        return None

def main():
    # Test case 1: Normal data
    line1 = '{"sensor_vlox":{"data":{"mm":170,"status":"ok"}},"sensor_imu":{"data":{"ax":0,"ay":0,"az":0,"status":"NA"}}}'
    data1 = parse_line(line1)
    print(f"Test 1 (Normal): TOF={data1.tof.mm}, Status={data1.tof.status}")
    assert data1.tof.mm == 170

    # Test case 2: Data with "49" (Ascii '1' ?)
    line2 = '{"sensor_vlox":{"data":{"mm":49,"status":"ok"}},"sensor_imu":{"data":{"ax":0,"ay":0,"az":0,"status":"NA"}}}'
    data2 = parse_line(line2)
    print(f"Test 2 (Value 49): TOF={data2.tof.mm}, Status={data2.tof.status}")
    
    # Test case 3: Missing data (defaults)
    line3 = '{"sensor_vlox":{},"sensor_imu":{}}'
    data3 = parse_line(line3)
    print(f"Test 3 (Missing): TOF={data3.tof.mm}, Status={data3.tof.status}")
    assert data3.tof.mm == 0

if __name__ == "__main__":
    main()
