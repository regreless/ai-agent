from langchain.agents import create_agent
from langchain_core.tools import tool

import config as config


@tool(description="获取身高,单位cm")
def get_height() -> int:
    return 170


@tool(description="获取体重,单位kg")
def get_weight() -> int:
    return 73


agent = create_agent(
    model=config.model,
    tools=[get_height, get_weight],
    system_prompt='你是严格遵循ReAct框架的智能体，必须按「思考→行动→观察→再思考」的流程解决问题，并告知你你的思考过程、工具的调用原因、按思考、行动、观察三个结构告知我,回答简洁务实'
)

res = agent.stream({
    "messages": [{"role": "user", "content": "计算我的BMI"}]},
    stream_mode="values"
)

for chunk in res:
    last_msg = chunk["messages"][-1]
    if last_msg.content:
        print(type(last_msg).__name__, last_msg.content)

    try:
        if last_msg.tool_calls:
            print(f"工具调用:{[tc['name'] for tc in last_msg.tool_calls]}")
    except AttributeError as e:
        pass
