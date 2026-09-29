"""基础演示：加载全部技能，连续测试两首诗和一次代码审查。"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import create_dw_agent
from src.hitl import HitlConfig
from src.sandbox import SandboxConfig

TEST_MESSAGES = [
    "飞流直下三千尺，疑是银河落九天",
    "举头望明月，低头思故乡",
    "帮我审查这段代码：\nconst data = await fetch('/api/users')\nconst users = data.json()\nconsole.log(users)",
]


def main():
    """复用同一个 Agent，观察技能切换和会话历史。"""
    agent = create_dw_agent(
        name="基础测试助手",
        sandbox=SandboxConfig(output_dir="output/demo-basic"),
        hitl=HitlConfig(enabled=False),
        system_prompt="回复简洁。第一行注明【使用技能：技能名称或无】。",
    )
    print("已加载技能：", "、".join(skill.name for skill in agent.get_skills()))
    for index, message in enumerate(TEST_MESSAGES, 1):
        print(f"\n测试 {index}：{message}")
        result = agent.invoke(message)
        print(result.content)
        print(f"历史消息数：{len(result.messages)}")
    print("输出文件：", agent.get_sandbox().list_files())
    print("请检查诗词是否幽默改写、代码审查是否指出缺少 await；技能标记仅为模型自述。")


if __name__ == "__main__":
    main()
