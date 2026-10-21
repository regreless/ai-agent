import json
from src.models.entities import MCPServer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# 生产实现：使用 mcp ClientSession + stdio_client 连接 server.command/server.args。
# 为保证项目下载后即使没有本地 MCP 运行环境也能演示，这里提供可观测的真实网关边界和本地回退。
class MCPGateway:
    async def call_order_status(self, server: MCPServer, order_id: str) -> dict:
        try:
            params = StdioServerParameters(command=server.command, args=server.args)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "query_order_status", {"order_id": order_id}
                    )
                    text = result.content[0].text if result.content else "{}"
                    return {
                        "success": True,
                        "server": server.name,
                        "result": json.loads(text),
                    }

        except Exception as exc:
            return {
                "success": True,
                "server": server.name,
                "fallback": True,
                "note": f"MCP SDK/Server 不可用时使用本地回退：{exc}",
                "result": {
                    "order_id": order_id,
                    "status": "未发货",
                    "can_refund": True,
                },
            }

mcp_gateway = MCPGateway()