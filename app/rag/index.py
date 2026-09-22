"""HTTP 入口：请求校验和路由。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.rag import service

router = APIRouter()


class RagDocument(BaseModel):
    id: str = Field(pattern=r"\S", description="文档 ID")
    content: str = Field(pattern=r"\S", description="文档正文")
    source: str | None = Field(default=None, description="来源，默认使用文档 ID")


class LoadRequest(BaseModel):
    documents: list[RagDocument] = Field(min_length=1, description="待追加的文档")


class SearchRequest(BaseModel):
    query: str = Field(pattern=r"\S", description="检索内容")
    top_k: int = Field(default=3, ge=1, le=100, strict=True)


class QueryRequest(BaseModel):
    question: str = Field(pattern=r"\S", description="用户问题")
    top_k: int = Field(default=3, ge=1, le=100, strict=True)


@router.post("/load", summary="加载文档")
def load_documents(load_request: LoadRequest):
    return service.load_documents(load_request.documents)


@router.post("/search", summary="向量检索")
def search(search_request: SearchRequest):
    return service.search(search_request.query, search_request.top_k)


@router.post("/query", summary="知识库问答")
def query(query_request: QueryRequest):
    return service.query(query_request.question, query_request.top_k)


@router.get("/status", summary="知识库状态")
def get_status():
    return service.get_status()


@router.delete("/clear", summary="清空知识库")
def clear_knowledge():
    return service.clear_knowledge()
