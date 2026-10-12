from pydantic import BaseModel, Field


class QueryOrderArgs(BaseModel):
    order_id: str = Field(..., min_length=1)


class QueryOrderResult(BaseModel):
    order_id: str
    status: str
    status_text: str
    tracking_company: str | None = None
    tracking_no: str | None = None
    latest_event: str | None = None


ORDERS = {
    "10001": dict(
        order_id="10001",
        status="shipped",
        status_text="已发货",
        tracking_company="顺丰",
        tracking_no="SF10001",
        latest_event="包裹已到达成都高新区中转站。",
    ),
    "10002": dict(order_id="10002", status="paid", status_text="已付款，待发货"),
}


async def query_order(order_id: str) -> QueryOrderResult:
    return QueryOrderResult(
        **ORDERS.get(
            order_id,
            dict(order_id=order_id, status="not_found", status_text="未查询到订单"),
        )
    )


def tool_schema():
    return {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "根据订单号查询订单状态和物流信息。用户询问订单、物流、发货状态时使用。",
            "parameters": QueryOrderArgs.model_json_schema(),
        },
    }


async def execute_tool(name, args):
    if name != "query_order":
        raise ValueError("工具不存在：" + name)
    valid = QueryOrderArgs.model_validate(args)
    return await query_order(valid.order_id)
