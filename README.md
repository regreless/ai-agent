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
uv run python app/main.py
```

接口文档：http://127.0.0.1:8000/docs。`app/main.py` 统一注册各模块 `index.py` 的 `router`，通过 `prefix` 设置路径前缀。

终端二启动 Streamlit：

```powershell
uv run streamlit run app/models/web.py
```

访问 http://localhost:8501，输入消息即可问答。接口地址和超时写在 `app/models/web.py` 顶部的 `API_URL` 和请求参数里，需要改动时直接改代码。

页面保留本次会话记录，但 `/models/chat` 每次只接收当前消息，不包含历史上下文。两个服务分别按 `Ctrl+C` 停止。

邮件审批页面使用同一个 FastAPI 后端，在终端二运行：

```powershell
uv run streamlit run app/graph/web.py
```

页面支持起草、修改、批准（模拟发送）、驳回和状态查询。侧栏可新建审批或输入已有线程 ID 继续审批；后端重启后，内存中的审批记录会丢失。

## MCP 接口

`app/mcp/index.py` 提供 HTTP 路由，`client.py` 负责 MCP 连接，`agent.py` 负责模型工具调用循环，`server.py` 注册并执行工具。每个请求自动启动并回收独立的 Python MCP 子进程。

仅提供 `POST /mcp/agent/run`：例如 `{"message":"查询姓张的学生"}`，模型自动获取并调用工具，最多 6 轮。

工具名称和参数使用下划线：`query_database(name, limit)`、`read_file(file_path)`、`get_weather(location)`。
数据库工具需要在项目根目录 `.env` 或环境变量中设置 `DATABASE_URL=postgresql://用户:密码@localhost:5432/数据库`，并存在 `student` 表及 `id`、`studentNo`、`name` 列。
文件工具仅返回路径提示，天气工具返回模拟数据，与原 Nest 示例一致。Agent 使用 `app/config.py` 中的 Ollama 配置。
需要单独提供 MCP 服务时运行 `uv run python -m app.mcp.server`，该服务通过标准输入输出通信，不监听 HTTP 端口。

## RAG 知识库

文件分工：`app/rag/index.py` 负责请求校验和路由，`service.py` 负责分块、向量化和问答，`database.py` 负责 ORM 模型、会话和数据库读写。

配置 `.env` 中的 `DATABASE_URL=postgresql://用户:密码@localhost:5432/数据库`，数据库需安装 pgvector，首次加载文档时自动创建扩展和表（数据库账号需要相应权限）。运行 `ollama pull mxbai-embed-large:latest` 下载向量模型；可通过 `OLLAMA_EMBED_MODEL` 指定模型，地址沿用 `app/config.py` 的 `llm.base_url`。

接口位于 `/rag`，请求与响应字段使用下划线命名：

- `POST /rag/load`：`{"documents":[{"id":"doc-1","content":"退款应在七天内申请。","source":"退款规则"}]}`，按 500 字分块，重叠 50 字；重复加载会追加。
- `POST /rag/search`：`{"query":"退款期限","top_k":3}`，返回余弦距离 `score` 和相似度 `similarity`。
- `POST /rag/query`：`{"question":"多久内可以申请退款？","top_k":3}`，只使用距离不大于 0.5 的资料回答，`sources` 与实际参考资料一致。
- `GET /rag/status`：查询当前集合的向量块数量。
- `DELETE /rag/clear`：清空当前集合，事务失败时回滚。

沿用 Nest 示例的 `langchain_pg_collection`、`langchain_pg_embedding` 表和 `rag-knowledge-base` 集合。指向同一数据库时会共享数据，清空也会影响 Nest 侧；复用数据必须使用相同的向量模型。
