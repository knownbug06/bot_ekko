from pydantic import BaseModel


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