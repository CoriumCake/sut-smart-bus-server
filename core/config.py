from pydantic_settings import BaseSettings
from pydantic import MongoDsn
from typing import Optional

class Settings(BaseSettings):
    MONGODB_URL: MongoDsn = "mongodb://localhost:27017/sut_smart_bus"
    
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    
    # Optional API Authentication
    # If set, all API requests must include X-API-Key header
    API_SECRET_KEY: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()

