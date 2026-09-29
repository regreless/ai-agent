"""搜索演示：Tavily 搜索 → DeepSeek 流式总结 → 保存学习笔记。"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import create_dw_agent
from src.hitl import HitlConfig
from src.sandbox import SandboxConfig
from src.tavily_search import TavilySearch

QUERY = "LangChain Deep Agents getting started official documentation"
FILE_NAME = "deep-agent-notes.md"


def main():
    """展示搜索结果，生成笔记并验证目标文件；搜索失败时停止。"""
    results = TavilySearch().search(QUERY)
    if not results:
        raise ValueError("搜索结果为空，请检查 Tavily Key、额度和网络")
    for result in results:
        print(f"{result.title}（{result.score:.2f}）\n{result.url}")
    sources = "\n\n".join(f"标题：{item.title}\n来源：{item.url}\n摘要：{item.content}" for item in results)

    agent = create_dw_agent(
        name="搜索笔记助手",
        sandbox=SandboxConfig(output_dir="output/demo-search"),
        hitl=HitlConfig(enabled=False),
    )
    result = agent.invoke_stream(
        "根据以下搜索资料生成中文学习笔记，包含核心概念、入门步骤、注意事项和来源链接。"
        "控制在 800 字以内。资料不足的地方明确说明，不编造。\n"
        f"请用 filename 围栏保存到 {FILE_NAME}。\n\n{sources}"
    )
    if FILE_NAME not in result.files_written:
        print("模型未按目标文件格式输出，将完整回复保存为笔记。")
        agent.write_file(FILE_NAME, result.content)
    content = agent.get_sandbox().read_file(FILE_NAME)
    if not content:
        raise ValueError("目标笔记未成功写入")
    print(f"\n文件：{agent.get_sandbox().output_path / FILE_NAME}")
    print(f"预览：\n{content[:400]}")


if __name__ == "__main__":
    main()
