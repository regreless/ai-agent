1. Type Hint 主要是类型提示
2. 默认不做运行时强校验
3. Pydantic BaseModel 会做运行时校验
4. 可以直接用于 FastAPI 请求体和响应体
5. Field 可以定义默认值、描述、校验规则
6. field_validator 和 model_validator 可以写业务校验
7. model_dump 和 model_dump_json 用于序列化
8. Pydantic 不只是 FastAPI 的请求模型
9. 它还可以服务 LLM Structured Output、Tool Calling、Agent State、RAG Document