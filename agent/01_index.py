from langchain.agents import create_agent
from langchain_core.tools import tool

import config as config


@tool(description="查询天气")
def get_weather() -> str:
    return '晴天'


@tool(description="查询企业信息")
def get_stock_info() -> str:
    return f"小米是一家港股上市公司"


agent = create_agent(
    model=config.model,
    tools=[get_weather, get_stock_info],
    system_prompt='你是一个聊天模型,回答简洁务实'
)

# res = agent.invoke({
#     "messages": [{"role": "user", "content": "明天上海天气咋样"}]
# })
#
# for msg in res["messages"]:
#     print(type(msg).__name__, msg.content)

res = agent.stream({
    "messages": [{"role": "user", "content": "小米是一家什样的企业"}]},
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
