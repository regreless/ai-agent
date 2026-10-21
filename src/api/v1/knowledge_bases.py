import os
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.api.deps import get_current_user
from src.core.config import get_settings
from src.db.session import get_db
from src.models.entities import KnowledgeBase, User
from src.schemas.common import ApiResponse
from src.services.rag.service import rag_service

router = APIRouter()


class KBCreate(BaseModel):
    name: str
    description: str = ""


@router.get("", response_model=ApiResponse[list[dict]])
async def list_kbs(
        db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    rows = ((
        await db.execute(select(KnowledgeBase).where(KnowledgeBase.tenant_id == user.tenant_id))
    )).scalars().all()
    return ApiResponse(
        data=[{"id": k.id, "name": k.name, "description": k.description} for k in rows]
    )


@router.post("", response_model=ApiResponse[dict])
async def create_kb(
        req: KBCreate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    kb = KnowledgeBase(
        tenant_id=user.tenant_id, name=req.name, description=req.description
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return ApiResponse(data={"id": kb.id, "name": kb.name})


@router.post("/{kb_id}/documents", response_model=ApiResponse[dict])
async def update_document(
        kb_id: str,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
):
    kb = (
        await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.tenant_id == user.tenant_id, KnowledgeBase.id == kb_id))
    ).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="KnowledgeBase not found")
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    safe_name = file.filename.replace("/", "_").replace("..", "_")
    file_path = os.path.join(settings.upload_dir, safe_name)
    content = await file.read()
    Path(file_path).write_bytes(content)
    result = await rag_service.ingest_document(
        db, user.tenant_id, kb, file_path, safe_name, file.content_type or ""
    )
    return ApiResponse(data=result)


@router.post("/{kb_id}/retrieval-test", response_model=ApiResponse[dict])
async def retrieval_test(
    kb_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = await rag_service.retrieve(
        db, user.tenant_id, [kb_id], body.get("query", ""), top_k=5
    )
    return ApiResponse(data={"results": results})
