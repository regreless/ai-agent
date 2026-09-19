# ai-agent

基于 Python 3.14、FastAPI 和 Ollama 的模型接口示例。

```powershell
# 创建虚拟环境并同步依赖
uv sync --locked

# 添加依赖
uv add 包名

# 运行脚本
uv run python 脚本名.py
```

提交 `pyproject.toml` 和 `uv.lock`，不提交 `.venv`。

## Streamlit 调试页面

确保本地 Ollama 已启动，并安装 `qwen3.5:0.8b` 模型。在项目根目录打开两个终端。

终端一启动 FastAPI：

```powershell
uv run python -m uvicorn app.models.index:app --reload
```

终端二启动 Streamlit（uv 自动准备独立工具环境，首次运行需要下载依赖）：

```powershell
uv tool run --with httpx streamlit run app/models/streamlit/index.py
```

访问 http://localhost:8501，输入消息即可调试。侧边栏可修改接口地址和超时，回答下方显示 token 用量、耗时和原始 JSON。

页面保留本次会话记录，但 `/models/chat` 每次只接收当前消息，不包含历史上下文。两个服务分别按 `Ctrl+C` 停止。
