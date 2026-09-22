"""MCP Server：注册三个工具，通过 stdio 接收客户端调用。"""

import os
from functools import cache
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from pydantic import Field
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
mcp_server = MCPServer("local-tools")


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_no: Mapped[str] = mapped_column("studentNo")
    name: Mapped[str]


@cache
def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("请在环境变量或项目 .env 中配置 DATABASE_URL")
    url = make_url(database_url).set(drivername="postgresql+psycopg")
    return create_engine(url, connect_args={"connect_timeout": 10})


@mcp_server.tool()
def query_database(
    name: str | None = None,
    limit: int = Field(default=10, gt=0),
) -> str:
    """查询 student 表，按姓名模糊匹配，默认最多返回 10 个学生。"""
    query = select(Student).order_by(Student.id).limit(limit)
    if name:
        query = query.where(Student.name.ilike(f"%{name}%"))
    # 同步工具由 MCP 在线程中执行，兼容 Windows 默认事件循环。
    with Session(get_engine()) as session:
        students = session.scalars(query).all()
    student_list = "\n".join(
        f"ID: {student.id}, Student No: {student.student_no}, Name: {student.name}"
        for student in students
    )
    return f"Found {len(students)} student(s):\n{student_list}"


@mcp_server.tool()
async def read_file(file_path: str) -> str:
    """文件读取演示：仅返回路径提示，不实际读取文件。"""
    return f"Reading file at path: {file_path}"


@mcp_server.tool()
async def get_weather(location: str) -> str:
    """天气查询演示：返回模拟的晴天、25°C，不代表实时天气。"""
    return f"The current weather in {location} is sunny with a temperature of 25°C."


if __name__ == "__main__":
    mcp_server.run(transport="stdio")
