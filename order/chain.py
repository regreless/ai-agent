"""Chain 顺序链 并行链 条件分支链

运行：python order/chain.py
依赖：python -m pip install langchain-ollama
需要启动本地 Ollama，并准备 qwen3.5:0.8b 模型。

"""

import asyncio
import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama

model = ChatOllama(
    model="qwen3.5:0.8b",
    base_url="http://localhost:11434",
    reasoning=False,
    temperature=0,
)

system_map = {
    "TECH": "你是技术支持助手，帮助用户解决技术问题。",
    "REFUND": "你是退款客服助手，帮助用户处理退款问题。",
    "ORDER": "你是订单助手，帮助用户处理订单问题。",
    "COMPLAINT": "你是投诉处理助手，帮助用户处理投诉建议。",
    "OTHER": "你是通用助手，帮助用户解答问题。",
}


# 公共方法：提示词 → 模型 → 字符串
def buildChain(prompt: ChatPromptTemplate):
    return prompt | model | StrOutputParser()


def printResult(title: str, result: dict[str, str]) -> None:
    print(f"\n{title}：", flush=True)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


# 保留原文并润色
async def polish(article: str) -> dict[str, str]:
    analysis_prompt = ChatPromptTemplate.from_template(
        "分析以下文章存在的问题，只输出问题列表：\n{article}"
    )

    polish_prompt = ChatPromptTemplate.from_template(
        "根据问题列表润色文章，改进表达、结构和用词，只输出润色后的文章。\n"
        "问题列表：{analysis}\n"
        "文章原文：{article}"
    )

    # 接收 {"article": 原文}，输出分析结果字符串。
    analysis_chain = buildChain(analysis_prompt)

    full_chain = (
        # 保留输入字典中的 article，并添加 analysis_chain 的分析结果。
            RunnablePassthrough.assign(analysis=analysis_chain)
            # 对照写法：替换上面的 assign 时，调用需改为 full_chain.ainvoke(article)。
            # {
            #     "article": RunnablePassthrough(),  # 原样传递输入的文章字符串
            #     "analysis": analysis_chain,       # 分析同一篇文章，输出问题列表
            # }
            | buildChain(polish_prompt)
    )
    result = await full_chain.ainvoke({"article": article})
    return {"original": article, "polish": result}


# 顺序链：大纲 → 文章 → SEO 标题
async def generateBlog(keywords: str, style: str) -> dict[str, str]:
    outline_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个博客大纲生成助手，根据用户提供的关键词和风格要求生成一篇博客文章的大纲"),
        ('human', '请根据以下关键词和风格要求生成一篇博客文章的大纲。关键词: {keywords}，风格要求: {style}')
    ])

    article_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个博客文章生成助手，根据用户提供的博客大纲和风格要求生成一篇博客文章。"),
        ('human', '请根据以下博客大纲和风格要求生成一篇博客文章。博客大纲: {outline}，风格要求: {style}')
    ])

    seo_title_prompt = ChatPromptTemplate.from_messages([
        ('system', '你是一个SEO标题生成助手，根据用户提供的博客文章内容和风格要求生成3个SEO标题。'),
        ('human', '请根据以下博客文章内容和风格要求生成3个SEO标题。博客文章内容: {article}，风格要求: {style}')
    ])

    outline_result = await buildChain(outline_prompt).ainvoke({"keywords": keywords, "style": style})
    article_result = await buildChain(article_prompt).ainvoke({"outline": outline_result, "style": style})
    seo_title_result = await buildChain(seo_title_prompt).ainvoke({"article": article_result, "style": style})
    return {"outline": outline_result, "article": article_result, "seo_titles": seo_title_result}


# 分类链 + 字典路由 + 回答链
async def smartRouter(question: str) -> dict[str, str]:
    # 1. 分类链：判断问题类型
    router_chain = buildChain(
        ChatPromptTemplate.from_messages([
            ("system",
             "判断问题类型，只输出一个标签：""技术问题 TECH；退款问题 REFUND；订单问题 ORDER；""投诉建议 COMPLAINT；其他 OTHER。"),
            ("human", "{question}")
        ])
    )

    category = (await router_chain.ainvoke({"question": question})).strip().upper()
    if category not in system_map:
        category = "OTHER"

    # 2. 条件分支：根据分类选择对应角色
    system_message = system_map[category]

    # 3. 回答链：使用选中的角色处理问题
    answer_chain = buildChain(
        ChatPromptTemplate.from_messages([("system", system_message), ("human", "{question}")])
    )

    answer = await answer_chain.ainvoke({"question": question})
    return {"question": question, "category": category, "answer": answer}


# 测试入口：调用方法，统一打印返回结果
async def main() -> None:
    # print("正在测试文章润色……", flush=True)
    # printResult("文章润色", await polish(
    #     "今天我学习了大模型。大模型很有用，可以做很多事情。我觉得学习很重要，所以我要继续学习大模型。"
    # ))

    # print("\n正在测试博客生成……", flush=True)
    # printResult("博客生成", await generateBlog(
    #     "Python、LangChain、文章自动生成",
    #     "面向初学者，通俗易懂、简洁务实，正文控制在300字以内",
    # ))

    print("\n正在测试智能路由……", end="", flush=True)
    printResult("智能路由", await smartRouter("我买的商品不想要了，怎么申请退款？"))


if __name__ == "__main__":
    asyncio.run(main())
