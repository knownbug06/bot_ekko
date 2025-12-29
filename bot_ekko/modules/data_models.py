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


