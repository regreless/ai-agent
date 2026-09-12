from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_agent, wrap_model_call, wrap_tool_call
from langchain_core.tools import tool
from langgraph.runtime import Runtime

import config as config

"""
before agent 
after agent 
before model
after model
tooling
modeling
"""


@tool(description="传入城市获取天气{city}")
def get_weather(city):
    return f"{city}的天气不错"


@before_agent
def before_agent(state: AgentState, runtime: Runtime) -> None:
    print("before agent", state["messages"])


@wrap_model_call
def model_call_hook(request, handle) -> None:
    return handle(request)


@wrap_tool_call
def tool_call_hook(request, handle) -> None:
    print(f"工具{request.tool_call['name']}")
    print(f"参数{request.tool_call['args']}")
    return handle(request)


agent = create_agent(
    model=config.model,
    tools=[get_weather],
    middleware=[before_agent, model_call_hook, tool_call_hook]
)

res = agent.stream({
    "messages": [{"role": "user", "content": "我在上海,今天天气咋样,穿衣有啥要求"}]},
    stream_mode="values"
)

for chunk in res:
    last_msg = chunk["messages"][-1]
    if last_msg.content:
        print(type(last_msg).__name__, last_msg.content)

    # try:
    #     if last_msg.tool_calls:
    #         print(f"工具调用:{[tc['name'] for tc in last_msg.tool_calls]}")
    # except AttributeError as e:
    #     pass
