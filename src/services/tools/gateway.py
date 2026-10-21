from sqlalchemy.ext.asyncio import AsyncSession
from src.models.entities import ToolDefinition


class ToolGateway:
    async def call(self, db: AsyncSession, tool: ToolDefinition, arguments: dict) -> dict:
        if tool.requires_approval:
            return {
                "status": "waiting_approval",
                "tool": tool.name,
                "arguments": arguments,
            }

        if tool.name == "query_order":
            order_id = arguments.get("order_id") or "10001"
            return {
                "success": True,
                "tool": tool.name,
                "order_id": order_id,
                "status": "未发货",
                "can_refund": True,
            }

        if tool.name == "create_ticket":
            return {
                "success": True,
                "tool": tool.name,
                "ticket_id": "TICKET-10001",
                "status": "created",
            }

        return {"success": True, "tool": tool.name, "result": "executed"}

tool_gateway = ToolGateway()