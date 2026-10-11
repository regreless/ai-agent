import asyncio
import time
from pydantic import BaseModel, Field
from typing import Any


class AgentRequest(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    order_id: str = Field(..., description="订单 ID")
    question: str = Field(..., description="用户问题")


async def query_user(user_id: str) -> dict[str, Any]:
    print("开始查询用户信息")
    await asyncio.sleep(1)
    print("用户信息查询完成")

    return {
        "user_id": user_id,
        "name": "大伟",
    }


async def query_order(order_id: str) -> dict[str, Any]:
    print("开始查询订单信息")
    await asyncio.sleep(1)
    print("订单信息查询完成")

    return {
        "order_id": order_id,
        "status": "已发货",
        "amount": 299
    }


async def query_logistics(order_id: str) -> dict[str, Any]:
    print("开始查询物流信息")
    await asyncio.sleep(2)
    print("物流信息查询完成")

    return {
        "order_id": order_id,
        "company": "顺丰",
        "status": "运输中",
        "eta": "明天送达"
    }


async def safe_call_tool(tool_name: str, coro, timeout: float = 2):
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return {
            "error": f"{tool_name} 调用超时"
        }
    except Exception as e:
        return {
            "error": f"{tool_name} 调用失败：{e}"
        }


async def call_llm(question: str,
                   user: dict[str, Any],
                   order: dict[str, Any],
                   logistics: dict[str, Any]) -> str:
    print("开始调用大模型生成最终回答")
    await asyncio.sleep(1)
    return (
        f"用户 {user['name']}，您的订单 {order['order_id']} 当前状态是"
        f"{order['status']}，物流公司是{logistics['company']}，"
        f"当前物流状态：{logistics['status']}，预计{logistics['eta']}。"
    )


async def agent_run(request: AgentRequest) -> str:
    user, order, logistics = await asyncio.gather(
        safe_call_tool("query_user", query_user(request.user_id)),
        safe_call_tool("query_order", query_order(request.order_id)),
        safe_call_tool("query_logistics", query_logistics(request.order_id)),
    )

    if "error" in logistics:
        return f"订单信息已查询到，但物流服务暂时不可用：{logistics['error']}"

    answer = await call_llm(
        question=request.question,
        user=user,
        order=order,
        logistics=logistics
    )

    return answer


async def main() -> None:
    start = time.perf_counter()
    request = AgentRequest(
        user_id="u_123",
        order_id="o_123",
        question="帮我查询一下订单物流状态"
    )
    answer = await agent_run(request)
    end = time.perf_counter()
    print(answer)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
