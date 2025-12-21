from pydantic_settings import BaseSettings
from pydantic import MongoDsn
from typing import Optional

class Settings(BaseSettings):
    MONGODB_URL: MongoDsn = "mongodb://localhost:27017/sut_smart_bus"
    
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    
    # Timezone
    TZ: str = "Asia/Bangkok"
    
    # OTA Firmware Directory
    FIRMWARE_DIR: str = "firmware"
    
    # Security Settings
    # If set, all API requests must include X-API-Key header
    API_SECRET_KEY: Optional[str] = None
    
    # Maximum firmware file size (2MB default - ESP32 typically < 1.5MB)
    MAX_UPLOAD_SIZE: int = 2 * 1024 * 1024  # 2MB in bytes
    
    # CORS allowed origins (comma-separated, or "*" for all)
    CORS_ORIGINS: str = "*"
    
    # Rate limiting (requests per minute)
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra fields in .env

settings = Settings()


