import asyncio, json, re, httpx
from collections.abc import AsyncGenerator
from src.core.config import settings
from src.llm.schemas import *


class BaseLLMProvider:
    async def chat(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError

    async def stream_chat(
        self, request: LLMRequest
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        raise NotImplementedError


class MockLLMProvider(BaseLLMProvider):
    async def chat(self, request: LLMRequest) -> LLMResponse:
        user = next(
            (m.content for m in reversed(request.messages) if m.role == LLMRole.user),
            request.messages[-1].content,
        )
        if request.tools and any(x in user for x in ["订单", "物流", "发货"]):
            match = re.search(r"\d{4,}", user)
            oid = match.group(0) if match else "10001"
            call = LLMToolCall(
                id="call_mock_order",
                name="query_order",
                arguments={"order_id": oid},
                raw_arguments=json.dumps({"order_id": oid}, ensure_ascii=False),
            )
            return LLMResponse(
                provider="mock",
                model=request.model,
                tool_calls=[call],
                finish_reason="tool_calls",
            )

        if any(m.role == LLMRole.tool for m in request.messages):
            raw = next(
                m.content for m in reversed(request.messages) if m.role == LLMRole.tool
            )
            data = json.loads(raw).get("data", {})
            text = f"您好，订单 {data.get('order_id')} 当前状态：{data.get('status_text')}。物流公司：{data.get('tracking_company') or '暂无'}，物流单号：{data.get('tracking_no') or '暂无'}，最新节点：{data.get('latest_event') or '暂无'}。"
            return self._resp(request, text)

        if request.response_format:
            joined = "\n".join(m.content for m in request.messages)
            if "RAG" in joined or "知识库" in joined:
                return self._resp(
                    request,
                    json.dumps(
                        {
                            "answer": "根据知识库片段，员工入职满一年后每年享有 5 天带薪年假。",
                            "is_answered": True,
                            "citations": ["doc_001"],
                            "missing_info": None,
                            "confidence": 0.9,
                        },
                        ensure_ascii=False,
                    ),
                )
            if "Agent" in joined or "任务规划" in joined or "工具" in joined:
                return self._resp(
                    request,
                    json.dumps(
                        {
                            "goal": user,
                            "need_tools": "订单" in user,
                            "steps": [
                                {
                                    "step_id": 1,
                                    "name": "理解目标",
                                    "action_type": "think",
                                    "tool_name": None,
                                    "arguments": {},
                                    "reason": "先判断需求",
                                }
                            ],
                            "final_response_style": "customer_service",
                        },
                        ensure_ascii=False,
                    ),
                )
            return self._resp(
                request,
                json.dumps(
                    {
                        "intent": "query_order" if "订单" in user else "other",
                        "confidence": 0.92,
                        "need_order_id": "订单" in user
                        and not re.search(r"\d{4,}", user),
                        "reply_strategy": (
                            "ask_order_id"
                            if "订单" in user and not re.search(r"\d{4,}", user)
                            else "answer_directly"
                        ),
                        "reason": "Mock 结构化输出",
                    },
                    ensure_ascii=False,
                ),
            )

        if "AI Agent" in user:
            text = "AI Agent 是能够理解目标、规划步骤、调用工具并根据结果完成任务的智能体。它比普通聊天机器人更强调行动能力。"
        elif "流式" in user or "Streaming" in user:
            text = "Streaming 流式输出就是模型边生成、后端边返回、前端边展示，适合实现 ChatGPT 一样的打字机效果。"
        else:
            text = "这是 Mock LLM 的演示回答：" + user
        return self._resp(request, text)

    def _resp(self, req: LLMRequest, text: str) -> LLMResponse:
        prompt_tokens = sum(len(m.content) for m in req.messages) // 2
        completion_tokens = len(text) // 2
        return LLMResponse(
            provider="mock",
            model=req.model,
            content=text,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            finish_reason="stop",
        )

    async def stream_chat(
        self, request: LLMRequest
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        result = await self.chat(request)
        for i in range(0, len(result.content), 8):
            await asyncio.sleep(0.02)
            yield LLMStreamChunk(
                provider="mock", model=request.model, content=result.content[i : i + 8]
            )
        yield LLMStreamChunk(
            provider="mock",
            model=request.model,
            usage=result.usage,
            finish_reason="stop",
        )


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self, provider: str, api_key: str, base_url: str):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def chat(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError(f"{self.provider} API Key 未配置")
        payload = {
            "model": request.model,
            "messages": [self._message_payload(m) for m in request.messages],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice
        if request.response_format:
            payload["response_format"] = request.response_format
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.base_url + "/chat/completions",
                headers={"Authorization": "Bearer " + self.api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        msg = data["choices"][0]["message"]
        usage = data.get("usage") or {}
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw)
            except Exception:
                args = {}
            calls.append(
                LLMToolCall(
                    id=tc.get("id", ""),
                    name=fn.get("name", ""),
                    arguments=args,
                    raw_arguments=raw,
                )
            )
        return LLMResponse(
            provider=self.provider,
            model=data.get("model", request.model),
            content=msg.get("content") or "",
            tool_calls=calls,
            finish_reason=data["choices"][0].get("finish_reason"),
            usage=LLMUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            ),
        )

    def _message_payload(self, message: LLMMessage) -> dict:
        payload = message.model_dump(exclude_none=True)
        payload["role"] = message.role.value
        return payload

    async def stream_chat(
        self, request: LLMRequest
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        result = await self.chat(request)
        yield LLMStreamChunk(
            provider=self.provider,
            model=request.model,
            content=result.content,
            usage=result.usage,
            finish_reason="stop",
        )


def get_provider() -> BaseLLMProvider:
    if settings.llm_provider == "deepseek":
        return OpenAICompatibleProvider(
            "deepseek", settings.deepseek_api_key, settings.deepseek_base_url
        )
    if settings.llm_provider == "qwen":
        return OpenAICompatibleProvider(
            "qwen", settings.dashscope_api_key, settings.qwen_base_url
        )
    if settings.llm_provider == "openai":
        return OpenAICompatibleProvider(
            "openai", settings.openai_api_key, settings.openai_base_url
        )
    return MockLLMProvider()
