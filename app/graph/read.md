# Graph 工作流

默认入口为 `index.py`，具体需求分别放在同级 Python 文件中。模型复用 `app.config.llm`。

| 文件              | 用途                                             |
| ----------------- | ------------------------------------------------ |
| chat.py           | 带历史的对话、历史查询                           |
| article.py        | 关键词和摘要                                     |
| react_agent.py    | 两数四则运算、模拟天气工具调用；组合计算分步调用 |
| routing.py        | 技术、价格、通用问题分类                         |
| parallel.py       | 拆分、并行处理、汇总                             |
| supervisor.py     | 研究、分析、写作节点调度                         |
| pipeline.py       | 素材、大纲、初稿、定稿                           |
| code_review.py    | 安全、性能、规范审查                             |
| email_approval.py | 起草、人工审批、修改及状态查询                   |

## 文件流程图

### chat.py

```mermaid
flowchart LR
    user_input[用户消息与 thread_id] --> load_history[读取会话历史]
    load_history --> call_model[结合历史生成回答]
    call_model --> save_history[保存会话]
    save_history --> chat_result[返回回答]
    history_query[历史查询与 thread_id] --> read_history[读取会话历史]
    read_history --> history_result[返回历史消息]
```

### article.py

```mermaid
flowchart LR
    article_input[文章] --> extract_keywords[提取关键词]
    extract_keywords --> generate_summary[生成摘要]
    generate_summary --> article_result[返回关键词与摘要]
```

### react_agent.py

```mermaid
flowchart LR
    user_input[用户消息与会话历史] --> call_model[模型生成回答或工具调用]
    call_model --> tool_check{是否调用工具}
    tool_check -->|是| run_tools[执行计算器或模拟天气工具]
    run_tools --> call_model
    tool_check -->|否| chat_result[返回回答]
```

### routing.py

```mermaid
flowchart LR
    user_input[用户问题] --> classify[模型分类]
    classify --> category{问题类别}
    category -->|technical| technical_handler[技术回答]
    category -->|pricing| pricing_handler[价格回答]
    category -->|general 或无效类别| general_handler[通用回答]
    technical_handler --> route_result[返回类别与回答]
    pricing_handler --> route_result
    general_handler --> route_result
```

### parallel.py

```mermaid
flowchart LR
    task_input[任务] --> split_task[拆分子任务]
    split_task --> dispatch_tasks[Send 动态并行分发]
    dispatch_tasks --> sub_task_a[处理子任务 A]
    dispatch_tasks --> sub_task_n[处理其余子任务]
    sub_task_a --> merge_results[合并结果并生成报告]
    sub_task_n --> merge_results
    merge_results --> task_result[返回综合报告]
```

子任务数量由拆分结果决定，最多 3 个；空输出时使用原任务。

### supervisor.py

```mermaid
flowchart LR
    user_input[用户任务] --> supervisor{协调者选择下一步}
    supervisor -->|研究| researcher[研究节点]
    supervisor -->|分析| analyst[分析节点]
    supervisor -->|写作| writer[写作节点]
    researcher --> supervisor
    analyst --> supervisor
    writer --> supervisor
    supervisor -->|结束| task_result[返回结果]
```

每个工作节点最多执行一次，执行顺序由协调者决定。

### pipeline.py

```mermaid
flowchart LR
    topic_input[文章主题] --> research_agent[整理素材]
    research_agent --> outline_agent[制定大纲]
    outline_agent --> writer_agent[撰写初稿]
    writer_agent --> review_agent[编辑定稿]
    review_agent --> article_result[返回文章]
```

### code_review.py

```mermaid
flowchart LR
    code_input[代码与语言] --> dispatch_reviews[并行分发审查任务]
    dispatch_reviews --> security_review[安全审查]
    dispatch_reviews --> performance_review[性能审查]
    dispatch_reviews --> style_review[规范审查]
    security_review --> generate_report[汇总评分与报告]
    performance_review --> generate_report
    style_review --> generate_report
    generate_report --> review_result[返回审查结果]
```

### email_approval.py

```mermaid
flowchart LR
    email_request[邮件需求] --> draft_node[起草邮件]
    draft_node --> wait_node[暂停等待人工审批]
    wait_node --> approval_action{恢复审批并处理决定}
    approval_action -->|批准| send_node[模拟发送]
    approval_action -->|驳回| cancel_node[取消邮件]
    approval_action -->|修改反馈| draft_node
    send_node --> email_result[结束]
    cancel_node --> email_result
    status_query[状态查询与 thread_id] --> read_status[读取当前审批状态]
    read_status --> status_result[返回状态与草稿]
```
