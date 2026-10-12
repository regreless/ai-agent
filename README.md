AI Chat
├── 最近对话缓存
├── session 状态
├── LLM 响应缓存
└── 用户调用频率限制

RAG
├── 检索结果缓存
├── embedding 任务状态
├── 文档解析进度
└── query cache

Agent
├── Agent Run 状态
├── 当前执行步骤
├── Tool Call 锁
├── 长任务进度
└── 中间结果缓存

平台能力
├── API Key 缓存
├── 登录态缓存
├── 验证码缓存
├── 分布式锁
└── 计数器

## 本地 Redis

使用 Docker 官方镜像 `redis:8.10.2-alpine`，仅绑定本机 `127.0.0.1:6379`，本地开发不设密码。
数据保存在 Docker 卷 `ai-agent_redis_data` 中，启用 AOF 持久化和容器自动重启。

```powershell
docker compose up -d --wait redis
docker compose exec redis redis-cli ping
docker compose stop redis
```

项目 `.env` 中配置 `REDIS_URL=redis://127.0.0.1:6379/0`。Python 连接示例：

```python
import os

from dotenv import load_dotenv
from redis import Redis

load_dotenv()
redis_client = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
print(redis_client.ping())
```

`docker compose down` 保留数据卷；不要使用 `down -v`，除非需要删除 Redis 数据。

## Redis Insight

```powershell
docker compose up -d redis_insight
```

浏览器打开 http://localhost:5540，已预配置 `ai-agent` 连接，数据库索引为 `0`。
Redis Insight 在 Docker 内通过 `redis:6379` 连接 Redis；桌面版则使用 `127.0.0.1:6379`，不填密码。
连接配置保存在 `ai-agent_redis_insight_data` 数据卷中。
