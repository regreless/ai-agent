"""固定协作流程：并行搜索 → 两个独立 Agent 并行分析 → 汇总报告。"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import create_dw_agent
from src.config import get_config
from src.hitl import HitlConfig
from src.sandbox import SandboxConfig
from src.tavily_search import TavilySearch

TOPICS = ["框架选型与对比", "前端与 AI 应用的协作方式"]
QUERIES = [
    "LangChain LangGraph Deep Agents official documentation comparison",
    "TypeScript AI agent frontend streaming human in the loop official documentation",
]
SAMPLE_DATA = [
    "离线示例需求：项目需要比较直接调用模型、固定工作流和带工具循环的 Agent。请从复杂度和可控性分析。",
    "离线示例需求：前端展示流式回复和审批状态，后端负责模型调用、工具执行和文件读写。请分析职责分工。",
]
FILE_NAME = "tech-research-report.md"


def researcher_agent(query, search):
    """搜索一个方向，保留来源；失败时中止，避免将空结果当作资料。"""
    results = search.search(query, 3)
    if not results:
        raise ValueError(f"搜索结果为空：{query}")
    return "\n\n".join(f"{item.title}\n{item.url}\n{item.content}" for item in results)


def analyst_agent(agent, topic, raw_data):
    """使用已初始化的独立 Agent 分析一个方向。"""
    result = agent.invoke(
        f"分析「{topic}」，输出 3～5 个要点，不超过 400 字，不写文件。"
        f"保留资料来源链接，区分资料事实与建议。\n资料：\n{raw_data}"
    )
    print(f"[分析完成] {topic}")
    return result.content


def writer_agent(sections, source_note):
    """汇总各部分，确保目标报告写入成功。"""
    agent = create_dw_agent(
        name="报告写手",
        sandbox=SandboxConfig(output_dir="output/demo-multi"),
        hitl=HitlConfig(enabled=False),
    )
    result = agent.invoke(
        "将以下内容整合成《前端 AI 智能体开发技术调研报告》，包含摘要、正文、结论和资料来源，"
        "总计不超过 1000 字。\n"
        f"资料说明：{source_note}，请在报告开头明确注明。\n"
        f"请用 filename 围栏保存到 {FILE_NAME}。\n\n" + "\n\n".join(sections)
    )
    if FILE_NAME not in result.files_written:
        print("模型未按目标文件格式输出，将完整回复保存为报告。")
        agent.write_file(FILE_NAME, result.content)
    content = agent.get_sandbox().read_file(FILE_NAME)
    if not content:
        raise ValueError("目标报告未成功写入")
    print(f"\n文件：{agent.get_sandbox().output_path / FILE_NAME}\n预览：\n{content[:500]}")


def main():
    """按固定顺序执行三个阶段；缺少 Tavily Key 时使用明确标注的示例资料。"""
    api_key = get_config().tavily_api_key.get_secret_value()
    raw_data = SAMPLE_DATA
    source_note = "离线示例需求分析，未进行网络搜索，不代表最新调研结论"
    with ThreadPoolExecutor(max_workers=2) as pool:
        if api_key:
            print("Step 1：并行搜索两个方向")
            search = TavilySearch(api_key)
            tasks = [pool.submit(researcher_agent, query, search) for query in QUERIES]
            raw_data = [task.result() for task in tasks]
            source_note = "基于本次 Tavily 搜索摘要及模型分析"
        else:
            print(f"Step 1：{source_note}")

        print("Step 2：两个独立 Agent 并行分析")
        # 先依次创建沙箱和会话，再并行请求模型。
        agents = [
            create_dw_agent(
                name=topic,
                sandbox=SandboxConfig(output_dir=f"output/demo-multi/analyst-{index}", verbose=False),
                hitl=HitlConfig(enabled=False),
            )
            for index, topic in enumerate(TOPICS, 1)
        ]
        tasks = [
            pool.submit(analyst_agent, agent, topic, data)
            for agent, topic, data in zip(agents, TOPICS, raw_data)
        ]
        sections = [task.result() for task in tasks]

    print("Step 3：汇总报告")
    writer_agent(sections, source_note)


if __name__ == "__main__":
    main()
