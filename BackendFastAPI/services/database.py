from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

class DatabaseService:
    _client: Optional[AsyncIOMotorClient] = None
    _db = None

    @classmethod
    def connect(cls, uri: str, db_name: str):
        cls._client = AsyncIOMotorClient(uri)
        cls._db = cls._client[db_name]

    @classmethod
    def get_db(cls):
        if cls._db is None:
            raise Exception("Database not connected. Call connect() first.")
        return cls._db