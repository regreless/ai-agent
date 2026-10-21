from fastapi import APIRouter
from src.api.v1 import (
    auth,
    agents,
    chat,
    costs,
    health,
    knowledge_bases,
    mcp_servers,
    models,
    roles,
    tools,
    traces,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(models.router, prefix="/models", tags=["Models"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles & Permissions"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(
    knowledge_bases.router, prefix="/knowledge-bases", tags=["Knowledge Bases"]
)
api_router.include_router(tools.router, prefix="/tools", tags=["Tools"])
api_router.include_router(
    mcp_servers.router, prefix="/mcp-servers", tags=["MCP Servers"]
)
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(traces.router, prefix="/traces", tags=["Traces"])
api_router.include_router(costs.router, prefix="/costs", tags=["Costs"])
