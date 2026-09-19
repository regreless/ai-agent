"""Pydantic 常用场景，结合 FastAPI。

运行示例：uv run python validate.py
启动接口：uv run --with uvicorn uvicorn validate:app --reload
接口文档：http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field, ValidationError


# 场景 1：检查用户提交的数据，如必填字段、名字长度、年龄范围。
class UserCreate(BaseModel):
    user_name: str = Field(min_length=2, max_length=20)
    age: int = Field(ge=0, le=150)
    # 允许为空，并且可以不传。
    phone_number: str | None = None


def show_validate_example():
    print("\n1. 校验数据")
    user_data = UserCreate(user_name="张三", age=18)
    print(user_data)

    try:
        UserCreate(user_name="李四", age=-1)
    except ValidationError as error:
        print("校验失败：", error.errors()[0]["msg"])


# 场景 2：将接口返回的字典或 JSON 转换为模型，方便通过属性访问。
def show_parse_example():
    print("\n2. 解析外部数据")
    # 默认允许部分类型转换，例如字符串 "18" 转为整数 18。
    user_data = UserCreate.model_validate({"user_name": "张三", "age": "18"})
    print(user_data.user_name, user_data.age)

    json_data = '{"user_name": "李四", "age": 20}'
    json_user = UserCreate.model_validate_json(json_data)
    print(json_user.user_name, json_user.age) 


# 场景 3：将模型转为字典或 JSON，用于数据传输。
def show_dump_example():
    print("\n3. 导出数据")
    user_data = UserCreate(user_name="张三", age=18)
    print("字典：", user_data.model_dump())
    print("JSON：", user_data.model_dump_json())


# 场景 4：FastAPI 自动校验请求体，并用响应模型控制返回字段。
class UserRead(BaseModel):
    user_id: int
    user_name: str
    age: int


app = FastAPI(title="Pydantic 常用场景")


@app.post("/users", response_model=UserRead, status_code=201)
def create_user(user_data: UserCreate) -> dict:
    """请求示例：{"user_name": "张三", "age": 18}。

    数据不合法时自动返回 422；本例仅模拟创建，不写数据库。
    响应只包含 UserRead 中的字段，不返回 phone_number。
    """
    return {"user_id": 1, **user_data.model_dump()}


if __name__ == "__main__":
    show_validate_example()
    show_parse_example()
    show_dump_example()
