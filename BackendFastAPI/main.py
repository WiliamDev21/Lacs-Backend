from fastapi import FastAPI
from services.database import DatabaseService
from contextlib import asynccontextmanager
from services.jwt_service import generate_and_store_secret_key
import os
from routers.router import add_cors_middleware, router

@asynccontextmanager
async def lifespan(_):
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DatabaseService.connect(mongo_uri, "lacs")
    generate_and_store_secret_key()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router= router)
add_cors_middleware(app)


