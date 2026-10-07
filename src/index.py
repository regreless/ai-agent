"""交互入口：npm run dev，支持连续对话、文件列表和清空历史。"""

import sys
from pathlib import Path
from urllib.error import HTTPError

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import create_dw_agent


def main():
    """创建一个持续运行的 Agent，普通输入使用流式回复。"""
    agent = create_dw_agent(
        name="大伟 OpenCodex",
        system_prompt=(
            "你擅长 Python、FastAPI、TypeScript、Vue、React、AI 应用开发、代码审查和技术文档。"
            "使用中文简洁回复，先说明执行步骤，再给出结果。"
        ),
    )
    print(f"\n{agent.name} 已就绪，模型：{agent.config.model}")
    print("已加载技能：", "、".join(skill.name for skill in agent.get_skills()))
    print("输入任务开始对话；clear 清空历史；files 查看文件；exit 退出。")

    while True:
        try:
            message = input("\n你：").strip()
            if not message:
                continue
            command = message.lower()
            if command == "exit":
                print("再见！")
                break
            if command == "clear":
                agent.clear_history()
                print("对话历史已清空。")
                continue
            if command == "files":
                files = agent.get_sandbox().list_files()
                print("\n".join(f"output/{name}" for name in files) or "还没有生成文件。")
                continue

            print(f"\n{agent.name}：")
            agent.invoke_stream(message)
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            break
        except HTTPError as error:
            print(f"请求失败：HTTP {error.code}，请检查密钥、额度和模型配置。")
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            print(f"处理失败：{error}，可继续输入。")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(f"启动失败：{error}")
