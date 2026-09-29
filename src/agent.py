"""Agent 核心：模型对话、技能提示词、人工确认和文件输出。"""

import json
import re
from dataclasses import dataclass
from urllib.request import Request, urlopen

from src.config import AgentConfig, get_config
from src.hitl import HitlConfig, hitl_checkpoint
from src.sandbox import SandboxConfig, create_sandbox
from src.skill_loader import SKILLS_DIR, build_skills_prompt, load_skills

# 外层围栏长度必须一致；文件内有代码块时，模型应使用四个反引号包裹文件。
FILE_BLOCK = re.compile(r"^(`{3,})(?:filename:|file:)([^\r\n]+)\r?\n(.*?)^\1[ \t]*\r?$", re.MULTILINE | re.DOTALL)


@dataclass
class AgentResult:
    content: str
    messages: list[dict[str, str]]
    files_written: list[str]


class DWAgent:
    def __init__(
        self,
        name: str = "大伟 Agent",
        config: AgentConfig | None = None,
        skills_dir=SKILLS_DIR,
        sandbox: SandboxConfig | None = None,
        hitl: HitlConfig | None = None,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """加载配置、技能和沙箱；每个实例维护独立的对话历史。"""
        self.name = name
        self.config = config or get_config()
        self.skills = load_skills(skills_dir)
        self.sandbox = create_sandbox(sandbox)
        self.hitl = hitl or HitlConfig()
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.conversation_history = []

    def build_system_prompt(self) -> str:
        """组合角色、全部技能、输出路径及用户自定义提示词。"""
        return (
            f"你是 {self.name}，一个基于 DeepSeek 的 AI 智能体。使用中文回复。\n"
            "先简要说明执行步骤，再给出结果。根据输入选择合适的技能。\n"
            f"{build_skills_prompt(self.skills)}\n"
            f"文件输出目录：{self.sandbox.output_path}\n"
            "需要保存文件时，用以下格式输出，文件名使用相对路径：\n"
            "```filename:notes.md\n文件内容\n```\n"
            "若文件内容含代码围栏，外层使用比内层更长的反引号围栏。\n"
            f"{self.system_prompt}"
        )

    def _request(self, messages: list[dict[str, str]], stream: bool) -> str:
        """请求模型；流式模式逐段打印，完整接收后返回文本。"""
        request = Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=json.dumps({
                "model": self.config.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": stream,
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            if not stream:
                choice = json.load(response)["choices"][0]
                if choice.get("finish_reason") == "length":
                    raise ValueError("回复被长度限制截断，本轮不保存历史和文件")
                return choice["message"].get("content") or ""

            content = ""
            for line in response:
                line = line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    print()
                    return content
                chunk = json.loads(data)
                if "error" in chunk:
                    raise ValueError("模型返回流式错误，本轮不保存历史和文件")
                for choice in chunk.get("choices", []):
                    if choice.get("finish_reason") == "length":
                        raise ValueError("回复被长度限制截断，本轮不保存历史和文件")
                    text = choice.get("delta", {}).get("content") or ""
                    print(text, end="", flush=True)
                    content += text
        raise ValueError("流式连接提前结束，本轮不保存历史和文件")

    def _invoke(self, user_message: str, stream: bool) -> AgentResult:
        """两种回复共用审批、历史和文件处理；请求失败时不修改历史。"""
        if not user_message.strip():
            raise ValueError("消息不能为空")
        if not hitl_checkpoint(user_message, self.hitl):
            return self._result("操作已被用户取消。", [])

        user_entry = {"role": "user", "content": user_message}
        messages = [
            {"role": "system", "content": self.build_system_prompt()},
            *self.conversation_history,
            user_entry,
        ]
        content = self._request(messages, stream)
        if not content.strip():
            raise ValueError("模型未返回有效文本")
        self.conversation_history.extend([user_entry, {"role": "assistant", "content": content}])
        return self._result(content, self.process_file_operations(content))

    def _result(self, content: str, files_written: list[str]) -> AgentResult:
        """返回历史快照，避免后续对话修改已有结果。"""
        messages = [message.copy() for message in self.conversation_history]
        return AgentResult(content, messages, files_written)

    def invoke(self, user_message: str) -> AgentResult:
        """普通调用：返回完整回复、对话历史和已写入的文件名。"""
        return self._invoke(user_message, stream=False)

    def invoke_stream(self, user_message: str) -> AgentResult:
        """流式调用：实时打印回复，结束后返回与普通调用相同的结果。"""
        return self._invoke(user_message, stream=True)

    def process_file_operations(self, content: str) -> list[str]:
        """提取 filename/file 围栏，通过人工检查后写入沙箱。"""
        files_written = []
        for _, filename, file_content in FILE_BLOCK.findall(content):
            filename = filename.strip()
            try:
                if hitl_checkpoint(f"写入文件：{filename}", self.hitl):
                    self.sandbox.write_file(filename, file_content.rstrip("\r\n"))
                    files_written.append(filename)
            except (ValueError, OSError) as error:
                print(f"[Agent] 写入失败 {filename}：{error}")
        return files_written

    def write_file(self, filename: str, content: str) -> str:
        """直接写入沙箱，供程序调用；与 TS 一样不额外经过人工确认。"""
        return self.sandbox.write_file(filename, content)

    def get_sandbox(self):
        """返回文件沙箱。"""
        return self.sandbox

    def get_skills(self):
        """返回已加载的技能。"""
        return self.skills

    def clear_history(self) -> None:
        """清空当前实例的对话历史。"""
        self.conversation_history.clear()


def create_dw_agent(**kwargs) -> DWAgent:
    """创建已初始化的 Agent，参数与 DWAgent 相同。"""
    return DWAgent(**kwargs)
