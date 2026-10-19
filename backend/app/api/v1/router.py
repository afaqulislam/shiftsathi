from fastapi import APIRouter

from app.api.v1.routes import (
    activity,
    auth,
    chat,
    dashboard,
    documents,
    health,
    incidents,
    knowledge,
    work_orders,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api_router.include_router(
    work_orders.router, prefix="/work-orders", tags=["work-orders"]
)
api_router.include_router(
    knowledge.router, prefix="/verified-knowledge", tags=["verified-knowledge"]
)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(activity.router, prefix="/activity", tags=["activity"])
