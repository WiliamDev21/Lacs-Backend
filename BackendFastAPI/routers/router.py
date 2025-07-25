from fastapi import APIRouter
from .user_endpoint import router as user_router
from .trabajador_endpoint import router as trabajador_router
from .admin_endpoint import router as admin_router
from .ubicaciones_endpoint import router as ubicaciones_router
from .auth_endpoint import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

router = APIRouter(prefix="/api", tags=["API"])
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(trabajador_router)
router.include_router(admin_router)
router.include_router(ubicaciones_router)


def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )