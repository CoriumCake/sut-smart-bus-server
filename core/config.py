from pydantic_settings import BaseSettings

from pydantic import MongoDsn

class Settings(BaseSettings):
    MONGODB_URL: MongoDsn = "mongodb://localhost:27017/sut_smart_bus"



    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883

    class Config:
        env_file = ".env"

settings = Settings()
