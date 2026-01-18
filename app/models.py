from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema_obj, handler):
        return core_schema.json_schema_string()

class MongoBaseModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True

class Bus(MongoBaseModel):
    bus_name: Optional[str] = None
    route_id: Optional[PyObjectId] = None
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None
    seats_available: int = 0
    mac_address: str = Field(..., unique=True)
    pm2_5: float = 0.0
    pm10: float = 0.0
    temp: float = 0.0
    hum: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class Stop(MongoBaseModel):
    name: str
    lat: float
    lon: float

class Route(MongoBaseModel):
    name: str
    description: Optional[str] = None
    stops: List[PyObjectId] = []

class Feedback(MongoBaseModel):
    name: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class HardwareLocation(MongoBaseModel):
    lat: float
    lon: float
    pm2_5: float = 0.0
    pm10: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    bus_mac: Optional[str] = "FAKE-PM-BUS"

class BlockedMAC(MongoBaseModel):
    mac_address: str = Field(..., unique=True)
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PMZone(MongoBaseModel):
    name: str = Field(...)
    points: List[List[float]] = []  # List of [lat, lon] points forming a polygon
    avg_pm25: float = 0.0
    avg_pm10: float = 0.0
    last_updated: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
