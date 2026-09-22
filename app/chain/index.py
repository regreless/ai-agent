from fastapi import APIRouter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field

from app.config import llm

router = APIRouter()


class PolishRequest(BaseModel):
    article: str = Field(
        pattern=r"\S",
        description="需要润色的文章",
        examples=["今天去公园，公园很好看，我很开心。"],
    )


class BlogRequest(BaseModel):
    keywords: str = Field(pattern=r"\S", description="博客关键词", examples=["Python 入门"])
    style: str = Field(pattern=r"\S", description="写作风格", examples=["简洁易懂"])


class RouterRequest(BaseModel):
    question: str = Field(pattern=r"\S", description="用户问题", examples=["如何申请退款？"])


@router.post(
    "/polish",
    summary="文章润色",
    description="顺序链：先分析文章问题，再保留原文并结合分析结果润色。",
)
async def polish(polish_request: PolishRequest):
    analysis_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是文章分析助手，只输出简洁的问题列表。"),
            ("human", "先分析这篇文章：{article}"),
        ]
    )
    polish_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是文章润色助手，根据问题列表改进表达，保留原意，只输出润色后的文章。",
            ),
            ("human", "分析结果：{analysis}\n原文：{article}"),
        ]
    )

    analysis_chain = analysis_prompt | llm | StrOutputParser()
    polish_chain = polish_prompt | llm | StrOutputParser()
    # 依次追加分析和润色结果，保留中间结果用于返回。
    full_chain = (
        RunnablePassthrough.assign(analysis=analysis_chain)
        | RunnablePassthrough.assign(polish=polish_chain)
    )
    result = await full_chain.ainvoke(polish_request.model_dump())
    return {
        "original": polish_request.article,
        "analysis": result["analysis"],
        "polish": result["polish"],
    }


@router.post(
    "/blog",
    summary="博客生成",
    description="顺序链：关键词和风格 → 大纲 → 文章 → SEO 标题，返回各步结果。",
)
async def generate_blog(blog_request: BlogRequest):
    outline_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是博客策划助手，根据关键词和风格生成简洁大纲，只输出大纲。"),
        ("human", "关键词：{keywords}\n风格：{style}"),
    ])
    article_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是博客写作助手，根据大纲和风格撰写简短文章，只输出正文。"),
        ("human", "大纲：{outline}\n风格：{style}"),
    ])
    seo_title_prompt = ChatPromptTemplate.from_messages([
        ("system", "你是 SEO 标题助手，根据文章生成 3 个简洁、贴合内容的标题，只输出标题列表。"),
        ("human", "文章：{article}\n风格：{style}"),
    ])

    outline_chain = outline_prompt | llm | StrOutputParser()
    article_chain = article_prompt | llm | StrOutputParser()
    seo_title_chain = seo_title_prompt | llm | StrOutputParser()
    # 每一步保留已有字段，追加结果，供下一步使用。
    full_chain = (
        RunnablePassthrough.assign(outline=outline_chain)
        | RunnablePassthrough.assign(article=article_chain)
        | RunnablePassthrough.assign(seo_title=seo_title_chain)
    )
    return await full_chain.ainvoke(blog_request.model_dump())


@router.post(
    "/router",
    summary="智能路由",
    description="先分类为技术、退款、订单、投诉或其他问题，再使用对应角色回答。",
)
async def smart_router(router_request: RouterRequest):
    router_prompt = ChatPromptTemplate.from_messages([
        ("system", "分析用户问题，只输出一个分类标签：\n"
         "技术问题：TECH\n退款问题：REFUND\n订单问题：ORDER\n"
         "投诉建议：COMPLAINT\n其他：OTHER"),
        ("human", "{question}"),
    ])
    router_chain = router_prompt | llm | StrOutputParser()
    category = await router_chain.ainvoke(router_request.model_dump())
    category = category.strip().upper()

    # 根据分类选择角色，无法识别的标签统一归为 OTHER。
    system_map = {
        "TECH": "你是技术支持助手，简洁解答技术问题。",
        "REFUND": "你是退款咨询助手，简洁说明退款申请方法。",
        "ORDER": "你是订单咨询助手，简洁说明订单查询和修改方法。",
        "COMPLAINT": "你是投诉处理助手，简洁说明投诉和跟进方法。",
        "OTHER": "你是通用助手，简洁回答用户问题。",
    }
    if category not in system_map:
        category = "OTHER"

    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", system_map[category]),
        ("human", "{question}"),
    ])
    answer_chain = answer_prompt | llm | StrOutputParser()
    answer = await answer_chain.ainvoke(router_request.model_dump())
    return {"question": router_request.question, "category": category, "answer": answer}
