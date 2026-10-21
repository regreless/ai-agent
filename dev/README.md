# 前端开发代理

旧版数据库若缺少聊天字段，运行一次增量迁移（保留历史数据，可重复执行）：

```powershell
uv run python dev/migrate_chat_schema.py
```

首次调用 `POST /api/v1/chat` 可省略 `conversation_id`，后端会创建会话并返回 ID。续聊时传回该 ID。
Embedding 输出维度须与 Qdrant 集合一致；默认 `QWEN_EMBEDDING_DIM`、`VECTOR_DIM` 均为 1024。
`DEEPSEEK_TIMEOUT_SECONDS` 默认 30 秒；模型调用超时返回 504，连接或上游接口错误返回 502。

前端请求使用相对地址 `/api/v1`。仅启动原来的 Vite 时，请求会到达前端端口而不会转发至 FastAPI；修改后端 CORS 不能解决这个问题。

在 ai-agent 目录启动后端（如果 8000 已有可用后端，无需重复启动）：

```powershell
uv run python src/main.py
```

`APP_DEBUG=true` 时，后端会监听 `src` 下的 Python 文件变化并自动重载，无需手动重启；设置 `APP_DEBUG=false` 可关闭。

停止原来的前端 Vite 进程，在 ai-agent 目录运行：

```powershell
node dev/start-frontend.mjs
```

访问 `http://localhost:5174`。脚本读取现有 frontend 配置，保留 Vue 插件，在运行时添加 `/api` 到 `http://localhost:8000` 的代理。无需修改 frontend 源码、Vite 配置或依赖文件。

登录、Swagger 和业务请求统一使用 `http://localhost:8000`，Swagger 地址为 `http://localhost:8000/docs`。8000 端口只运行一套后端，避免 IPv4 和 IPv6 命中不同服务。

后端启动需要可用的 PostgreSQL，连接信息从 ai-agent 的 `.env` 读取；首次启动会创建表并初始化管理员。默认登录邮箱 `admin@example.com`，密码 `admin123456`，可通过 `DEFAULT_ADMIN_EMAIL`、`DEFAULT_ADMIN_PASSWORD` 配置。

可通过环境变量指定前端目录、后端地址或前端端口：

```powershell
$env:FRONTEND_DIR = 'C:\AIApp\enterprise_ai_agent_platform_real\frontend'
$env:BACKEND_URL = 'http://localhost:8000'
$env:FRONTEND_PORT = '5174'
node dev/start-frontend.mjs
```

端口已占用时脚本会报错，不会自动换端口。此脚本用于本地开发；生产部署应由网关或 Nginx 转发 `/api`。
