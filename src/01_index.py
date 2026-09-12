import os
from openai import OpenAI
import config.index as config

client = OpenAI(api_key=os.environ.get(config.api_key), base_url=config.base_url)

response = client.chat.completions.create(
    model=config.model,
    messages=[
        {"role": "system", "content": "你是一个Python专家，说话简单务实"},
        {"role": "assistant", "content": "我是Python专家，非常靠谱"},
        {"role": "user", "content": "小红有一只猫"},
        {"role": "assistant", "content": "好的"},
        {"role": "user", "content": "小红有两只狗"},
        {"role": "assistant", "content": "好的"},
        {"role": "user", "content": "小红一共有几个宠物"},
    ],
    stream=True,
)
for chunk in response:
    content = chunk.choices[0].delta.content
    if content is not None:
        print(content, end="", flush=True)

example_data = {
    "新闻报道": "AI芯片需求持续增长",
    "财务报道": "公司季度营收同比增长18%",
    "公司公告": "公司宣布启动股份回购计划",
    "分析师报告": "机构上调公司目标价至120元"
}

question = [
    {"AI芯片需求持续增长"},
    {"公司季度营收同比增长18%"},
    {"公司宣布启动股份回购计划"},
    {"机构上调公司目标价至120元"},
    {"员工食堂本周新增川菜窗口"}
]

messages = [{"role": "system",
             "content": "你是一个金融专家，说话简单务实 将文本分为[新闻报道，财务报道，公司公告，分析师报告]，不清楚分类为不清楚"}, ]

for key, value in example_data.items():
    messages.append({"role": "user", "content": value})
    messages.append({"role": "assistant", "content": key})

for q in question:
    response = client.chat.completions.create(
        model=config.model,
        messages=messages + [{"role": "user", "content": f"按照示例回复类别${q}"}],
        # stream=True
    )
    print(response.choices[0].message.content)
