import time
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import (
    Agent,
    AgentRun,
    Conversation,
    CostRecord,
    MCPServer,
    Message,
    ModelProvider,
    ToolDefinition,
)
from src.services.llm.gateway import llm_gateway
from src.services.mcp.gateway import mcp_gateway
from src.services.rag.service import rag_service
from src.services.tools.gateway import tool_gateway
from src.services.trace.service import trace_service


class AgentWorkflowEngine:
    async def run(
            self,
            db: AsyncSession,
            tenant_id: str,
            user_id: str,
            agent_id: str,
            message: str,
            conversation_id: str | None = None
    ) -> dict:
        agent = (await db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if not agent:
            raise ValueError("Agent not found")
        model = (await db.execute(
            select(ModelProvider).where(ModelProvider.id == agent.model_provider_id)
        )).scalar_one()
        if not conversation_id:
            conv = Conversation(
                tenant_id=tenant_id,
                user_id=user_id,
                agent_id=agent_id,
                title=message[:50]
            )
            db.add(conv)
            await db.commit()
            conversation_id = conv.id
        db.add(Message(conversation_id=conversation_id, role='user', content=message))
        run = AgentRun(
            tenant_id=tenant_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            user_id=user_id,
            status="running"
        )
        db.add(run)
        await db.flush()
        trace_id = f"trace_{uuid.uuid4().hex[:16]}"

        await trace_service.add_span(
            db,
            trace_id,
            run.id,
            "agent.config.load",
            "runtime",
            output={"agent": agent.name, "mode": agent.mode},
        )
        t = time.time()
        sources = await rag_service.retrieve(
            tenant_id, agent.knowledge_base_ids or [], message, top_k=5
        )
        await trace_service.add_span(
            db,
            trace_id,
            run.id,
            "rag.retrieve",
            "rag",
            input={"query": message},
            output={"sources": sources},
            latency_ms=int((time.time() - t) * 1000),
        )
        tool_results = []
        for tool_id in agent.tool_ids or []:
            tool = (await db.execute(
                select(ToolDefinition).where(ToolDefinition.id == tool_id)
            )).scalar_one_or_none()
            if tool and tool.enabled:
                args = (
                    {"order_id": "10001"}
                    if "订单" in message or "退款" in message
                    else {}
                )
                t = time.time()
                res = await tool_gateway.call(db, tool, args)
                tool_results.append(res)
                await trace_service.add_span(
                    db,
                    trace_id,
                    run.id,
                    f"tool.call.{tool.name}",
                    "tool",
                    input=args,
                    output=res,
                    latency_ms=int((time.time() - t) * 1000)
                )

        mcp_results = []
        for service_id in agent.mcp_server_ids or []:
            server = (
                await db.execute(select(MCPServer).where(MCPServer.id == service_id))
            ).scalar_one_or_none()
            if server and server.enabled:
                t = time.time()
                res = await mcp_gateway.call_order_status(server, "10001")
                mcp_results.append(res)
                await trace_service.add_span(
                    db,
                    trace_id,
                    run.id,
                    f"mcp.call.{server.name}",
                    "mcp",
                    output=res,
                    latency_ms=int((time.time() - t) * 1000),
                )

        context = "\n".join(item["payload"].get("content", "") for item in sources)
        messages = [
            {"role": "system", "content": agent.system_prompt},
            {
                "role": "user",
                "content": f"用户问题：{message}\n\n知识库上下文：{context}\n\nTool结果：{tool_results}\n\nMCP结果：{mcp_results}",
            },
        ]
        t = time.time()
        llm = await llm_gateway.chat(model, messages)
        await trace_service.add_span(
            db,
            trace_id,
            run.id,
            "llm.call",
            "llm",
            input={"provider": model.provider, "model": model.model_name},
            output={
                "input_tokens": llm.input_tokens,
                "output_tokens": llm.output_tokens,
            },
            latency_ms=int((time.time() - t) * 1000),
        )
        db.add(Message(conversation_id=conversation_id, role='assistant', content=llm.content))
        cost = (
                llm.input_tokens / 1000 * model.input_price_per_1k
                + llm.output_tokens / 1000 * model.output_price_per_1k
        )
        db.add(CostRecord(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent.id,
            run_id=run.id,
            provider=model.provider,
            model_name=model.model_name,
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            total_cost=cost,
        ))

        await trace_service.add_span(
            db, trace_id, run.id, "cost.record", "cost", output={"cost": round(cost, 6)}
        )

        run.status = "success"
        run.final_answer = llm.content
        run.total_tokens = llm.input_tokens + llm.output_tokens
        run.total_cost = round(cost, 6)
        await db.commit()
        return {
            "run_id": run.id,
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "answer": llm.content,
            "sources": sources,
            "tool_results": tool_results,
            "mcp_results": mcp_results,
            "cost": round(cost, 6),
        }


workflow_engine = AgentWorkflowEngine()
