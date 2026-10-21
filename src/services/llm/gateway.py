from dataclasses import dataclass
import json
from openai import AsyncOpenAI
from src.core.config import get_settings
from src.models.entities import ModelProvider


@dataclass
class LLMResult:
    content: str
    input_tokens: int
    output_tokens: int
    raw: dict


class LLMGateway:

    def _estimate_tokens(self, text: str) -> int:
        chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other = len(text) - chinese
        return chinese + max(1, other // 4)

    async def chat(self, model: ModelProvider, messages: list[dict], temperature: float = 0.2) -> LLMResult:
        provider = model.provider.lower()
        if provider == "deepseek":
            return await self._deepseek_chat(model, messages, temperature)
        return self._mock_chat(messages)

    async def _deepseek_chat(self, model: ModelProvider, messages: list[dict], temperature: float) -> LLMResult:
        settings = get_settings()
        api_key = settings.deepseek_api_key
        if not api_key:
            return self._mock_chat(messages, reason="DEEPSEEK_API_KEY 未配置，使用本地回退回答。")
        async with AsyncOpenAI(
            api_key=api_key,
            base_url=settings.deepseek_base_url,
            timeout=settings.deepseek_timeout_seconds,
            max_retries=0,
        ) as client:
            resp = await client.chat.completions.create(
                model=model.model_name or settings.deepseek_model,
                messages=messages,
                temperature=temperature,
            )
        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        return LLMResult(
            content=content,
            input_tokens=getattr(
                usage,
                "prompt_tokens",
                self._estimate_tokens(json.dumps(messages, ensure_ascii=False)),
            ),
            output_tokens=getattr(
                usage, "completion_tokens", self._estimate_tokens(content)
            ),
            raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )

    def _mock_chat(self, messages: list[dict], reason: str = "") -> LLMResult:
        content = (
            "【本地回退回答】根据知识库和工具结果，如果订单未发货，可以申请退款；"
            "如果已发货，需要走售后流程或转人工。"
        )
        if reason:
            content += f"\n\n说明：{reason}"
        return LLMResult(
            content=content,
            input_tokens=self._estimate_tokens(
                json.dumps(messages, ensure_ascii=False)
            ),
            output_tokens=self._estimate_tokens(content),
            raw={"provider": "mock"},
        )


llm_gateway = LLMGateway()
