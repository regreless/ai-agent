"""Agent：模型选择工具，MCP 执行工具，再将结果交给模型。"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.config import llm
from app.mcp.client import TOOL_TIMEOUT, open_session

MAX_ROUNDS = 6


async def run_agent(message: str):
    async with open_session() as session:
        llm_with_tools = llm.bind_tools(
            [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                }
                for tool in (await session.list_tools()).tools
            ]
        )
        messages = [
            SystemMessage(
                content="你是智能助手，根据问题选择工具获取信息后用中文回答。"
                "文件和天气工具是演示，必须如实说明模拟结果；工具失败时不要编造结果。"
            ),
            HumanMessage(content=message),
        ]
        steps: list[str] = []
        for round_count in range(1, MAX_ROUNDS + 1):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)
            if not response.tool_calls:
                return {
                    "message": message,
                    "steps": steps,
                    "total_rounds": round_count,
                    "answer": response.content,
                }
            for tool_call in response.tool_calls:
                steps.append(
                    f"调用工具: {tool_call['name']}，参数: {tool_call['args']}"
                )
                try:
                    tool_result = await session.call_tool(
                        tool_call["name"],
                        tool_call["args"],
                        read_timeout_seconds=TOOL_TIMEOUT,
                    )
                    result_text = tool_result.model_dump_json(
                        by_alias=True, exclude_none=True
                    )
                except Exception as error:
                    result_text = f"工具调用失败: {error}"
                steps.append(f"工具执行结果: {result_text}")
                messages.append(
                    ToolMessage(content=result_text, tool_call_id=tool_call["id"])
                )
        return {
            "message": message,
            "steps": steps,
            "total_rounds": MAX_ROUNDS,
            "answer": "已达到最大执行轮数，未获得最终回答。",
            "error": "max_rounds_reached",
        }
