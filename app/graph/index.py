"""Graph 默认入口：请求校验与路由注册，具体工作流按需求拆分。"""

from typing import Annotated

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field

from app.graph import article, chat, code_review, email_approval, parallel, pipeline, react_agent, routing, supervisor

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(pattern=r"\S", description="用户消息")


class MemoryChatRequest(ChatRequest):
    thread_id: str = Field(pattern=r"\S", description="会话标识，相同标识共享上下文")


class ArticleRequest(BaseModel):
    article: str = Field(pattern=r"\S", description="待提取关键词和摘要的文章")


class InputRequest(BaseModel):
    input: str = Field(pattern=r"\S", description="问题或任务")


class ParallelRequest(BaseModel):
    task: str = Field(pattern=r"\S", description="需要拆分并行处理的任务")


class PipelineRequest(BaseModel):
    topic: str = Field(pattern=r"\S", description="文章主题")


class CodeReviewRequest(BaseModel):
    code: str = Field(pattern=r"\S", description="待审查代码")
    language: str = Field(default="TypeScript", pattern=r"\S")


class EmailRequest(BaseModel):
    request: str = Field(pattern=r"\S", description="邮件起草需求")
    thread_id: str = Field(pattern=r"\S", description="新的审批线程标识")


class ModifyRequest(BaseModel):
    feedback: str = Field(pattern=r"\S", description="修改意见")


@router.post("/memory-chat", summary="有记忆对话")
async def memory_chat(body: MemoryChatRequest):
    return await chat.memory_chat(body.thread_id, body.message)


@router.get("/history/{thread_id}", summary="会话历史")
async def get_history(thread_id: Annotated[str, Path(pattern=r"\S")]):
    return await chat.get_history(thread_id)


@router.post("/article", summary="文章关键词和摘要")
async def process_article(body: ArticleRequest):
    return await article.process(body.article)


@router.post("/react-chat", summary="ReAct 工具调用对话")
async def react_chat(body: MemoryChatRequest):
    return await react_agent.chat(body.thread_id, body.message)


@router.post("/route", summary="问题分类路由")
async def route_chat(body: InputRequest):
    return await routing.route_chat(body.input)


@router.post("/parallel", summary="拆分任务并行处理")
async def parallel_chat(body: ParallelRequest):
    return await parallel.parallel_chat(body.task)


@router.post("/supervisor", summary="协调者调度工作节点")
async def supervisor_chat(body: InputRequest):
    return await supervisor.run(body.input)


@router.post("/pipeline", summary="内容生成流水线")
async def process_pipeline(body: PipelineRequest):
    return await pipeline.process(body.topic)


@router.post("/code-review", summary="多维度并行代码审查")
async def review_code(body: CodeReviewRequest):
    return await code_review.review(body.code, body.language)


@router.post("/email/start", summary="起草邮件并等待审批")
async def start_email(body: EmailRequest):
    return await email_approval.start(body.request, body.thread_id)


@router.post("/email/{thread_id}/approve", summary="批准邮件（模拟发送）")
async def approve_email(thread_id: Annotated[str, Path(pattern=r"\S")]):
    return await email_approval.resume(thread_id, "approve")


@router.post("/email/{thread_id}/reject", summary="驳回邮件")
async def reject_email(thread_id: Annotated[str, Path(pattern=r"\S")]):
    return await email_approval.resume(thread_id, "reject")


@router.post("/email/{thread_id}/modify", summary="修改草稿并重新等待审批")
async def modify_email(thread_id: Annotated[str, Path(pattern=r"\S")], body: ModifyRequest):
    return await email_approval.resume(thread_id, "modify", body.feedback)


@router.get("/email/{thread_id}/status", summary="查询邮件审批状态")
async def email_status(thread_id: Annotated[str, Path(pattern=r"\S")]):
    return await email_approval.get_status(thread_id)
