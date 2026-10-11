from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator


class ToolName(str, Enum):
    QUERY_ORDER = "query_order"
    QUERY_PRODUCT = "query_product"
    QUERY_LOGISTICS = "query_logistics"


class ToolCall(BaseModel):
    tool_name: ToolName = Field(alias="tool_name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具参数")


class OrderQueryArguments(BaseModel):
    order_id: str = Field(..., min_length=1, description="订单 ID")

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("order_id 必须是数字字符串")

        return value


tool_call = ToolCall(tool_name=ToolName.QUERY_ORDER, arguments={"order_id": "1001"})

order_args = OrderQueryArguments(**tool_call.arguments)

print(tool_call.model_dump())
print(order_args.model_dump())