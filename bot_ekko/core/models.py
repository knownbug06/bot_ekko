from pydantic import BaseModel
from typing import Optional
from enum import Enum


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
    x: int
    y: int


class CommandNames(Enum):
    CHANGE_STATE = "change_state"


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
