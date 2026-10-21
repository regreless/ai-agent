from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import get_settings
from src.core.security import hash_password
from src.models.entities import (
    Agent,
    KnowledgeBase,
    MCPServer,
    ModelProvider,
    Tenant,
    ToolDefinition,
    User,
)


async def seed(db: AsyncSession):
    settings = get_settings()
    tenant = (
        await db.execute(select(Tenant).where(Tenant.code == "demo"))
    ).scalar_one_or_none()
    if not tenant:
        tenant = Tenant(name="Demo 企业", code="demo")
        db.add(tenant)
        await db.flush()
    user = (
        await db.execute(select(User).where(User.email == settings.default_admin_email))
    ).scalar_one_or_none()
    if not user:
        user = User(
            tenant_id=tenant.id,
            email=settings.default_admin_email,
            name="Admin",
            hashed_password=hash_password(settings.default_admin_password),
            is_admin=True,
        )
        db.add(user)
    model = (
        await db.execute(
            select(ModelProvider).where(
                ModelProvider.tenant_id == tenant.id,
                ModelProvider.provider == "deepseek",
            )
        )
    ).scalar_one_or_none()
    if not model:
        model = ModelProvider(
            tenant_id=tenant.id,
            provider="deepseek",
            model_name=settings.deepseek_model,
            display_name="DeepSeek Chat",
            base_url=settings.deepseek_base_url,
            input_price_per_1k=0.001,
            output_price_per_1k=0.002,
        )
        db.add(model)
        await db.flush()
    kb = (
        await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.tenant_id == tenant.id,
                KnowledgeBase.name == "售后退款知识库",
            )
        )
    ).scalar_one_or_none()
    if not kb:
        kb = KnowledgeBase(
            tenant_id=tenant.id,
            name="售后退款知识库",
            description="企业售后、退款、物流政策。",
        )
        db.add(kb)
        await db.flush()
    tool = (
        await db.execute(
            select(ToolDefinition).where(
                ToolDefinition.tenant_id == tenant.id,
                ToolDefinition.name == "query_order",
            )
        )
    ).scalar_one_or_none()
    if not tool:
        tool = ToolDefinition(
            tenant_id=tenant.id,
            name="query_order",
            description="查询订单状态",
            schema={"order_id": "string"},
            risk_level="low",
        )
        db.add(tool)
        await db.flush()
    mcp = (
        await db.execute(
            select(MCPServer).where(
                MCPServer.tenant_id == tenant.id, MCPServer.name == "订单 MCP Server"
            )
        )
    ).scalar_one_or_none()
    if not mcp:
        mcp = MCPServer(
            tenant_id=tenant.id,
            name="订单 MCP Server",
            description="标准 MCP stdio 示例服务",
            command=settings.mcp_order_command,
            args=settings.mcp_order_args.split(),
            tools=["query_order_status"],
        )
        db.add(mcp)
        await db.flush()
    agent = (
        await db.execute(
            select(Agent).where(
                Agent.tenant_id == tenant.id, Agent.code == "customer_service"
            )
        )
    ).scalar_one_or_none()
    if not agent:
        agent = Agent(
            tenant_id=tenant.id,
            name="电商客服 Agent",
            code="customer_service",
            description="真实企业级客服 Agent，支持 RAG、Tool、MCP。",
            system_prompt="你是企业电商客服 Agent，回答必须基于知识库、工具和 MCP 结果。回答要简洁，涉及不确定业务时提示转人工。",
            model_provider_id=model.id,
            knowledge_base_ids=[kb.id],
            tool_ids=[tool.id],
            mcp_server_ids=[mcp.id],
            mode="rag_tool_mcp",
            status="published",
        )
        db.add(agent)
    await db.commit()
