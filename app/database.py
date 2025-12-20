from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

# Create a single client instance
client = AsyncIOMotorClient(str(settings.MONGODB_URL))

# Get a reference to the database
db = client.get_database()

# You can also access collections directly, e.g., db.buses
# This setup allows us to import 'db' from this module in other parts of the app.
