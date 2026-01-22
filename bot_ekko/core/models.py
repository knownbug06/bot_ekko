from __future__ import annotations

from typing import List
from pydantic import BaseModel
from typing import Optional
from enum import Enum

from typing import Dict, Any, Union
import json

from bot_ekko.core.logger import get_logger

logger = get_logger("Models")


class TOFSensorData(BaseModel):
    mm: int
    status: str


class IMUSensorData(BaseModel):
    ax: float
    ay: float
    az: float


class SensorData(BaseModel):
    tof: TOFSensorData
    imu: IMUSensorData


class StateContext(BaseModel):
    state: str
    state_entry_time: int
    x: float
    y: float
    params: Optional[dict] = None


class CommandNames(Enum):
    CHANGE_STATE = "change_state"
    RESTORE_STATE = "restore_state"


class CommandCtx(BaseModel):
    name: CommandNames
    params: Optional[dict] = None

    def __str__(self):
        return f"{self.name}: {self.params}"
    
    def __repr__(self):
        return self.__str__()
    

class BluetoothData(BaseModel):
    text: str
    is_connected: Optional[bool] = False


class ServiceSensorConfig(BaseModel):
    name: str
    baud: int
    port: str

    sensor_triggers: Dict[str, Union[str, Dict[str, int]]]
    proximity_duration: int = 10
    sensor_update_rate: float = 0.1


class ServiceBluetoothConfig(BaseModel):
    name: str
    
    

class ServicesConfig(BaseModel):
    sensor_service: ServiceSensorConfig
    bt_service: ServiceBluetoothConfig

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)

    @classmethod
    def from_json_file(cls, file_path: str):
        with open(file_path, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded services config from {file_path}")
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()
