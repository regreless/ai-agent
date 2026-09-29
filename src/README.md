# Python Agent 迁移

参考 `read.txt`，逐步将 agent-ts 迁移为 Python + FastAPI。迁移内容统一放在当前目录，Python 模块直接位于此处，不再嵌套一层 src，也不需要 TypeScript 的 dist 和构建配置。

## 快速测试

```powershell
cd C:\AIApp\ai-agent\src
npm run dev
```

启动后加载全部技能，直接输入任意内容，由模型根据技能的触发条件选择，例如：

```text
你：举头望明月，低头思故乡
你：帮我审查这段代码：const users = fetch('/api/users');
你：给一个 FastAPI 待办事项服务写 README
你：exit
```

`npm` 仅作为快捷命令入口，底层由 `uv` 运行 Python，无需 `npm install`。

## 第一步：API Key 配置

- `.env`：本机实际配置，不提交 Git。
- `.env.example`：可提交的配置模板，不包含实际密钥。
- `config.py`：加载当前目录的 `.env`，同名系统环境变量优先，不读取父目录 `.env`。
- `get_config()`：返回配置；缺少 DeepSeek 密钥时明确报错。密钥使用 `SecretStr`，常规打印配置时隐藏密钥。
- `TAVILY_API_KEY`：搜索功能的密钥，通过 `config.tavily_api_key` 读取；仅聊天时可留空，同样支持系统环境变量覆盖。

目前沿用项目根目录的 Python 环境及已有 dotenv、Pydantic 依赖。在 `ai-agent` 根目录验证配置：

```powershell
uv run python -c "from src.config import get_config; config = get_config(); print(config)"
```

此命令仅验证配置读取，不请求模型。实际调用 SDK 时使用 `config.api_key.get_secret_value()`，不要将其写入日志。

## 第二步：Skill 加载

`skill_loader.py` 默认读取同目录下 `.dw/skills/*.skill.md`，不受启动目录影响，无需 API Key 即可加载。已迁移诗词笑话、代码审查、文档生成三个技能。

- `parse_skill_file(file_path)`：解析名称、Description、Script、Examples、References，并保留原文。
- `load_skills()`：返回技能列表；支持指定目录，目录不存在或为空时返回空列表。
- `build_skills_prompt(skills)`：生成提示词，包含完整执行步骤、示例和参考资料。由模型根据触发条件选择技能，Script 是文字说明，不直接执行代码。

```python
from src.skill_loader import build_skills_prompt, load_skills

skills = load_skills()
system_prompt = build_skills_prompt(skills)
```

也可绕过 npm，在项目根目录直接启动交互脚本：

```powershell
uv run python -X utf8 src/demo_skill.py
```

启动仅加载技能；输入非空内容后才请求 DeepSeek API。输入 `exit` 或按 Ctrl+C 退出；空输入跳过，请求失败后可继续输入。每条输入独立处理，暂不保存对话历史。没有匹配技能时正常回答。

脚本不执行回复中的代码或文件操作。回复首行的技能名称是模型自述，需结合回复是否遵循技能步骤判断效果，并非程序记录的触发事件。

Agent 核心见第五步；FastAPI 尚未接入。

## 第三步：文件沙箱

`sandbox.py` 对应 TS 的 `sandbox.ts`，默认输出到 `src/output`，不受启动目录影响。

```python
from src.sandbox import create_sandbox

sandbox = create_sandbox()
sandbox.write_file("reports/note.md", "测试内容")
print(sandbox.read_file("reports/note.md"))
print(sandbox.list_files())
print(sandbox.is_path_safe("../config.py"))  # False
```

通过 `SandboxConfig(workspace_path=..., output_dir="output", verbose=False)` 可自定义工作区。写入自动创建子目录并覆盖同名文件；读取越界或不存在的文件返回 `None`；列表按名称排序，使用相对路径。

路径校验使用解析后的真实路径，拦截父目录越界、相似前缀目录和指向外部的符号链接。此模块是文件路径限制，不是操作系统级沙箱，也不防御其他进程并发替换路径。Agent 已接入模型回复的自动写文件流程。

在项目根目录运行测试：

```powershell
uv run python -m unittest discover -s src/tests -p "test_sandbox.py" -v
```

## 第四步：人工确认

`hitl.py` 对应 TS 的 `hitl.ts`，保留关键词检查、自定义关键词、开关和自动批准。使用同步 `input()` 实现终端确认：

```python
from src.hitl import HitlConfig, hitl_checkpoint

config = HitlConfig(extra_keywords=["覆盖文件"])
if hitl_checkpoint("覆盖文件 notes.md", config):
    print("允许继续")  # 在这里调用实际操作
```

默认开启检查；普通操作直接通过，危险操作只有输入 `y` 或 `yes` 才通过。`enabled=False` 关闭检查，`auto_approve=True` 用于自动批准。Agent 已在请求模型前和自动写文件前接入检查；后续 FastAPI 审批需改为 HTTP 状态和恢复接口，不能直接等待终端输入。

```powershell
uv run python -m unittest discover -s src/tests -p "test_hitl.py" -v
```

## 第五步：Agent 核心

`agent.py` 对应 TS 的 `agent.ts`，复用已有配置、Skill、沙箱和 HITL，不新增依赖。初始化在构造方法中完成，普通与流式请求共用处理逻辑。

```python
from src.agent import create_dw_agent

agent = create_dw_agent(name="大伟 Agent")
result = agent.invoke("给一个待办事项服务写 README，保存为 README.md")
print(result.content)
print(result.files_written)

agent.invoke_stream("把刚才的介绍缩短一些")  # 实时打印，保留本实例的会话历史
agent.clear_history()
```

可选参数：`config`（`src.config.AgentConfig`，配置模型、地址和密钥）、`skills_dir`、`sandbox`、`hitl`、`system_prompt`、`temperature`、`max_tokens`。默认使用 `src/.env`，文件写入 `src/output`。`get_skills()`、`get_sandbox()` 和 `write_file()` 保留原有用途。

普通及流式调用返回 `AgentResult(content, messages, files_written)`。请求失败或回复截断时不保存本轮历史和文件。文件写入失败会打印原因，其余文件继续处理。每个实例用于串行对话，历史只保存在内存。

当前为同步调用，流式内容打印到终端；不是 FastAPI 的 SSE 接口。模型回复内的 `filename:` 或 `file:` 围栏会自动写文件，若文件内容包含代码块，需使用更长的外层围栏。

```powershell
uv run python -m unittest discover -s src/tests -p "test_agent.py" -v
```

## 第六步：Tavily 搜索

`tavily_search.py` 对应 TS 的 `tavily-search.ts`，沿用标准库请求，不新增依赖。

```python
from src.tavily_search import TavilySearch

search = TavilySearch()  # 从已有配置读取 TAVILY_API_KEY，也可直接传入密钥
results = search.search("FastAPI 入门", max_results=3)
for result in results:
    print(result.title, result.url, result.content, result.score)
```

保留 `basic` 搜索、默认最多 5 条结果、摘要截取前 800 字和失败返回空列表的行为。缺少密钥时初始化报错，网络请求超时为 30 秒。当前为同步工具，尚未接入 Agent 的自动工具选择；需要由调用方搜索后把结果传给 Agent。

```powershell
uv run python -m unittest discover -s src/tests -p "test_tavily_search.py" -v
```

## 第七步：三个端到端演示

在 `src` 目录执行，无需 `npm install`：

```powershell
cd C:\AIApp\ai-agent\src
npm run demo:basic
npm run demo:search
npm run demo:multi
```

| 命令 | 测试范围 | 所需密钥 | 输出目录 |
| --- | --- | --- | --- |
| `demo:basic` | 两首诗的幽默改写、代码审查、连续会话 | DeepSeek | `src/output/demo-basic`（有文件输出时） |
| `demo:search` | Tavily 搜索、流式总结、笔记写入 | DeepSeek、Tavily | `src/output/demo-search/deep-agent-notes.md` |
| `demo:multi` | 并行搜索、独立 Agent 并行分析、报告汇总 | DeepSeek；Tavily 可选 | `src/output/demo-multi/tech-research-report.md` |

脚本分别对应 `demo_basic.py`、`demo_search.py`、`demo_multi_agent.py`，也可从项目根目录通过 `uv run python -X utf8 src/脚本名.py` 运行。

这些是会实际调用 API 的演示，沿用 TS 演示关闭 HITL。基础演示观察诗词改写和缺少 `await` 的问题是否被识别；模型自述的技能名不等于确定的触发记录。搜索和协作演示会验证目标文件非空，未按目标文件格式输出时保存完整回复作为回退。重复运行会覆盖同名演示文件。

多 Agent 演示使用线程池实现两个同步调用并行，每个分析任务使用独立会话和输出目录。没有 Tavily Key 时使用离线示例需求，仍调用 DeepSeek；配置了 Tavily 但搜索失败时直接报错，不伪装成成功。流程由代码固定编排。

## 后续迁移顺序

1. 交互入口及 FastAPI 接口。
2. HTTP 人工审批和恢复。
