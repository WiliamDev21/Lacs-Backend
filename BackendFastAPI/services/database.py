from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

class DatabaseService:
    _client: Optional[AsyncIOMotorClient] = None
    _db = None

    @classmethod
    def connect(cls, uri: str, db_name: str):
        # Configurar cliente con timeouts más largos para operaciones masivas
        cls._client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=30000,  # 30 segundos
            connectTimeoutMS=30000,          # 30 segundos  
            socketTimeoutMS=300000,          # 5 minutos para operaciones largas
            maxPoolSize=50,                  # Más conexiones concurrentes
            retryWrites=True,                # Reintentar escrituras automáticamente
            w='majority'                     # Esperar confirmación de escritura
        )
        cls._db = cls._client[db_name]

    @classmethod
    def get_db(cls):
        if cls._db is None:
            raise Exception("Database not connected. Call connect() first.")
        return cls._db

# Función de dependencia para FastAPI
def get_database():
    """Función de dependencia para obtener la base de datos en los endpoints"""
    return DatabaseService.get_db()