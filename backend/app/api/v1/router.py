from fastapi import APIRouter

from app.api.v1.routers import (
    admin,
    auth,
    claims,
    flags,
    notifications,
    posts,
    ranking,
    reviews,
    social,
    stores,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(stores.router)
api_router.include_router(reviews.router)
api_router.include_router(flags.router)
api_router.include_router(ranking.router)
api_router.include_router(posts.router)
api_router.include_router(social.router)
api_router.include_router(claims.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
