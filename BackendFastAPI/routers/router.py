from .user_endpoint import router as user_router
from .trabajador_endpoint import router as trabajador_router
from .admin_endpoint import router as admin_router
from fastapi.middleware.cors import CORSMiddleware

all_routers = [
    user_router,
    trabajador_router,
    admin_router
]


def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
