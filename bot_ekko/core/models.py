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

    status: str


class GestureData(BaseModel):
    gesture: str
    score: float
    status: str


class SensorData(BaseModel):
    tof: TOFSensorData
    imu: IMUSensorData


class StateContext(BaseModel):
    state: str
    state_entry_time: int
    # Deprecated: x/y kept for backward compatibility if needed, but prefer physics_state
    x: float = 0.0 
    y: float = 0.0
    physics_state: Optional[Dict[str, Any]] = None
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
    enabled: bool = False

    sensor_triggers: Dict[str, Union[str, Dict[str, int]]]
    proximity_duration: int = 10
    sensor_update_rate: float = 0.1


class ServiceBluetoothConfig(BaseModel):
    name: str
    enabled: bool = False
    

class ServiceGestureConfig(BaseModel):
    name: str
    enabled: bool = False
    socket_path: str = "/tmp/ekko_ipc.sock"
    gesture_update_rate: float = 0.1
    
    # Optional mappings if needed in config
    gesture_state_mapping: Optional[Dict[str, str]] = {}


class ServiceSystemLogsConfig(BaseModel):
    name: str
    enabled: bool = False
    sample_rate: float = 10.0
    log_file: Optional[str] = None


class UIExpressionConfig(BaseModel):
    adapter_module_path: str = "bot_ekko.ui_expressions_lib.eyes.adapter"
    adapter_class_name: str = "EyesExpressionAdapter"


class ServicesConfig(BaseModel):
    sensor_service: ServiceSensorConfig
    bt_service: ServiceBluetoothConfig
    gesture_service: ServiceGestureConfig
    system_logs_service: Optional[ServiceSystemLogsConfig]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)


class SystemConfig(BaseModel):
    ui_expression_config: UIExpressionConfig
    services: ServicesConfig

    @classmethod
    def from_json_file(cls, file_path: str):
        with open(file_path, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded system config from {file_path}")
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()
