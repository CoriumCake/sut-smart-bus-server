from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import List, Optional, Annotated, Any
from datetime import datetime
from bson import ObjectId

PyObjectId = Annotated[str, BeforeValidator(str)]

# --- Bus Schemas ---
class BusBase(BaseModel):
    bus_name: Optional[str] = None
    current_lat: float
    current_lon: float
    seats_available: int
    pm2_5: float = 0.0
    pm10: float = 0.0
    temp: float = 0.0
    hum: float = 0.0
    last_updated: Optional[datetime] = None
    mac_address: Optional[str] = None # Added for consistency

class BusCreate(BusBase):
    id: int
    route_id: int

class Bus(BusBase):
    id: int
    route_id: int

    class Config:
        from_attributes = True

# Schema for incoming bus location updates from hardware
class BusLocation(BaseModel):
    bus_mac: str
    bus_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    seats_available: int
    pm2_5: float
    pm10: float
    temp: Optional[float] = 0.0
    hum: Optional[float] = 0.0

# --- Route Schemas ---
class RouteBase(BaseModel):
    name: str
    description: Optional[str] = None
    bus_id: Optional[str] = None # Linked Bus ID

class RouteCreate(RouteBase):
    id: int

class Route(RouteBase):
    id: int
    buses: List[Bus] = []

    class Config:
        from_attributes = True

# --- Stop Schemas ---
class StopBase(BaseModel):
    name: str
    lat: float
    lon: float

class StopCreate(StopBase):
    id: int

class Stop(StopBase):
    id: int

    class Config:
        from_attributes = True

# --- Feedback Schemas ---
class FeedbackBase(BaseModel):
    name: str
    message: str

class FeedbackCreate(FeedbackBase):
    pass

class Feedback(FeedbackBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Hardware Location Schemas ---
class HardwareLocationBase(BaseModel):
    lat: float
    lon: float
    pm2_5: float
    pm10: float

class HardwareLocationCreate(HardwareLocationBase):
    pass

class HardwareLocation(HardwareLocationBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# --- PM Zone Schemas ---
class PMZoneBase(BaseModel):
    name: str
    points: List[List[float]] = []

class PMZoneCreate(PMZoneBase):
    # Allow creating providing lat/lon center + radius (for circular approximation)
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius: Optional[float] = 50.0

class PMZone(PMZoneBase):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    avg_pm25: float
    avg_pm10: float
    last_updated: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
