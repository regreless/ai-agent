import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("tenant")
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("user")
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("role")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(128))
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("ur")
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    role_id: Mapped[str] = mapped_column(String(64), index=True)


class ModelProvider(Base, TimestampMixin):
    __tablename__ = "model_providers"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("provider")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(64))  # deepseek / ollama
    model_name: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(128))
    base_url: Mapped[str] = mapped_column(String(255), default="")
    api_key_ref: Mapped[str] = mapped_column(String(128), default="")
    input_price_per_1k: Mapped[float] = mapped_column(Float, default=0.0)
    output_price_per_1k: Mapped[float] = mapped_column(Float, default=0.0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("agent")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128))
    code: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    model_provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("model_providers.id")
    )
    knowledge_base_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    tool_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    mcp_server_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String(64), default="rag_tool_mcp")
    status: Mapped[str] = mapped_column(String(32), default="published")
    version: Mapped[str] = mapped_column(String(32), default="v1")


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_bases"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("kb")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    embedding_provider: Mapped[str] = mapped_column(String(64), default="qwen")
    vector_collection: Mapped[str] = mapped_column(
        String(128), default="enterprise_agent_chunks"
    )


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("doc")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kb_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("knowledge_bases.id"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="uploaded")


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("chunk")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    kb_id: Mapped[str] = mapped_column(String(64), index=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255), default="")
    vector_id: Mapped[str] = mapped_column(String(128), index=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)


class ToolDefinition(Base, TimestampMixin):
    __tablename__ = "tool_definitions"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("tool")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    schema: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class MCPServer(Base, TimestampMixin):
    __tablename__ = "mcp_servers"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("mcp")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    command: Mapped[str] = mapped_column(String(255), default="python")
    args: Mapped[list[str]] = mapped_column(JSON, default=list)
    tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("conv")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255), default="新会话")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("msg")
    )
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("run")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    final_answer: Mapped[str] = mapped_column(Text, default="")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)


class TraceSpan(Base, TimestampMixin):
    __tablename__ = "trace_spans"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("span")
    )
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="success")
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)


class CostRecord(Base, TimestampMixin):
    __tablename__ = "cost_records"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("cost")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    model_name: Mapped[str] = mapped_column(String(128))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    embedding_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uid("audit")
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(128))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
