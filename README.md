| 表名 | 作用 | 关键关联字段 |
|---|---|---|
| `tenants` | 租户，即企业或组织，作为资源隔离边界 | `id`、唯一的 `code` |
| `users` | 用户账号，保存登录信息、启用状态、管理员标记 | `tenant_id` |
| `roles` | 租户内的权限角色，权限列表存于 JSON 字段 `permissions` | `tenant_id` |
| `user_roles` | 用户与角色的关联表，支持一个用户拥有多个角色 | `user_id`、`role_id` |
| `model_providers` | 模型调用配置：提供方、模型名、接口地址、密钥引用及单价 | `tenant_id` |
| `agents` | 智能体配置：提示词、模型、知识库、工具、MCP、模式和版本 | `model_provider_id`、三组资源 ID 数组 |
| `knowledge_bases` | 知识库配置，组织文档并记录向量相关配置 | `tenant_id` |
| `documents` | 上传文件的元数据：文件名、路径、类型、处理状态 | `kb_id`、`tenant_id` |
| `document_chunks` | 文档切片正文、来源、Token 数及向量索引 ID | `document_id`、`kb_id`、`vector_id` |
| `tool_definitions` | 工具定义：参数 schema、风险等级、审批标记、启用状态 | `tenant_id` |
| `mcp_servers` | MCP 服务配置：启动命令、参数、工具名称列表 | `tenant_id` |
| `conversations` | 会话容器，记录谁与哪个 Agent 对话 | `tenant_id`、`user_id`、`agent_id` |
| `messages` | 会话中的逐条消息，保存角色和正文 | `conversation_id` |
| `agent_runs` | Agent 每次执行的记录：状态、最终回答、总 Token 和费用 | `conversation_id`、`user_id`、`agent_id` |
| `trace_spans` | 执行步骤日志，例如检索、工具调用、模型调用及耗时 | `run_id`、`trace_id`、`parent_span_id` |
| `cost_records` | 调用用量与费用明细，支持按用户、Agent、模型统计 | `run_id`、`tenant_id`、`user_id`、`agent_id` |
| `audit_logs` | 操作审计，记录操作者、动作、资源和细节 | `user_id`、`resource_type`、`resource_id` |



```mermaid
%%{init: {
  "layout": "elk",
  "theme": "base",
  "flowchart": {
    "curve": "linear",
    "nodeSpacing": 40,
    "rankSpacing": 55,
    "padding": 15
  },
  "themeVariables": {
    "primaryColor": "#102a40",
    "primaryTextColor": "#9cd1ff",
    "primaryBorderColor": "#20394b",
    "lineColor": "#687782",
    "edgeLabelBackground": "#0d1117",
    "fontSize": "12px"
  }
}}%%

flowchart TB
    model_providers["model_providers 模型配置"]
    agents["agents 智能体"]
    tenants["tenants 租户"]
    users["users 用户"]
    tenant_resources["租户资源：角色 / 模型 / Agent<br/>/ 知识库 / 工具 / MCP"]
    roles["roles 角色"]
    user_roles["user_roles 用户角色关联"]

    tool_definitions["tool_definitions 工具"]
    knowledge_bases["knowledge_bases 知识库"]
    mcp_servers["mcp_servers MCP"]
    documents["documents 文档"]
    document_chunks["document_chunks 切片"]

    conversations["conversations 会话"]
    agent_runs["agent_runs 单次执行"]
    messages["messages 消息"]
    trace_spans["trace_spans 步骤日志"]
    cost_records["cost_records 费用明细"]

    model_providers --> agents

    tenants --> users
    tenants --> tenant_resources
    users --> conversations
    users --> user_roles
    roles --> user_roles

    agents -. "JSON ID 数组，多对多" .-> tool_definitions
    agents -. "JSON ID 数组，多对多" .-> knowledge_bases
    agents -. "JSON ID 数组，多对多" .-> mcp_servers
    agents --> conversations

    knowledge_bases --> documents
    documents --> document_chunks

    conversations --> agent_runs
    conversations --> messages
    agent_runs --> trace_spans
    agent_runs --> cost_records

    classDef table fill:#102a40,stroke:#20394b,stroke-width:1px,color:#9cd1ff,rx:10,ry:10;
    class model_providers,agents,tenants,users,tenant_resources,roles,user_roles,tool_definitions,knowledge_bases,mcp_servers,documents,document_chunks,conversations,agent_runs,messages,trace_spans,cost_records table;

    linkStyle default stroke:#687782,stroke-width:1px;
```





