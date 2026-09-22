import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.chain.index import router as chains_router
from app.graph.index import router as graph_router
from app.models.index import router as models_router
from app.mcp.index import router as mcp_router
from app.prompts.index import router as prompts_router
from app.rag.index import router as rag_router

app = FastAPI()
app.include_router(graph_router, prefix="/graph", tags=["LangGraph 工作流"])
app.include_router(models_router, prefix="/models", tags=["模型对话"])
app.include_router(prompts_router, prefix="/prompts", tags=["提示词"])
app.include_router(chains_router, prefix="/chains", tags=["链"])
app.include_router(mcp_router, prefix="/mcp", tags=["MCP"])
app.include_router(rag_router, prefix="/rag", tags=["知识库"])


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
