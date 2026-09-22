from fastapi import APIRouter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, FewShotPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field

from app.config import llm

router = APIRouter()


class TranslateRequest(BaseModel):
    text: str = Field(pattern=r"\S", description="需要翻译的文本")
    target_language: str = Field(pattern=r"\S", description="目标语言")


class SummarizeRequest(BaseModel):
    text: str = Field(pattern=r"\S", description="需要总结的文本")
    max_words: int = Field(gt=0, description="总结的最大字数")


class ClassifyRequest(BaseModel):
    text: str = Field(pattern=r"\S", description="需要进行情感分类的文本")


class CodeReviewRequest(BaseModel):
    code: str = Field(pattern=r"\S", description="需要审查的代码")
    language: str = Field(pattern=r"\S", description="编程语言")


@router.post(
    "/translate", summary="文本翻译",
    description="from_messages：system 定义角色，human 提供任务，模板变量传入文本和目标语言。",
)
async def translate(translate_request: TranslateRequest):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个翻译助手，将文本翻译成指定语言，只输出翻译结果。"),
        ("human", "请把以下内容翻译成 {target_language}: {text}"),
    ])
    chain = prompt | llm | StrOutputParser()
    result = await chain.ainvoke(translate_request.model_dump())
    return {"original": translate_request.text, "translation": result}


@router.post(
    "/summarize", summary="文本总结",
    description="from_template：单条消息模板，通过变量设置文本和字数要求；提示词不保证严格限字。",
)
async def summarize(summarize_request: SummarizeRequest):
    prompt = ChatPromptTemplate.from_template(
        "请把以下内容总结成不超过 {max_words} 个字的版本，只输出总结结果：{text}"
    )
    chain = prompt | llm | StrOutputParser()
    result = await chain.ainvoke(summarize_request.model_dump())
    return {
        "original": summarize_request.text,
        "max_words": summarize_request.max_words,
        "summary": result,
    }


@router.post(
    "/classify", summary="情感分类",
    description="FewShotPromptTemplate：提供输入、输出示例，引导模型分类为积极、消极或中立。",
)
async def classify(classify_request: ClassifyRequest):
    examples = [
        {"text": "今天天气真好，我们去公园玩吧", "label": "积极"},
        {"text": "我讨厌这个产品，太差了", "label": "消极"},
        {"text": "这个电影还行，有些地方不错", "label": "中立"},
        {"text": "这很失望，我不会买了", "label": "消极"},
    ]
    prompt = FewShotPromptTemplate(
        examples=examples,
        example_prompt=PromptTemplate.from_template("输入：{text}\n输出：{label}"),
        prefix="请对输入文本进行情感分类，只输出积极、消极或中立，不要解释。",
        suffix="输入：{text}\n输出：",
        input_variables=["text"],
    )
    chain = prompt | llm | StrOutputParser()
    result = await chain.ainvoke(classify_request.model_dump())
    return {"text": classify_request.text, "label": result.strip()}


@router.post(
    "/code-review", summary="代码审查",
    description="角色设定与多变量模板：根据编程语言和代码，生成错误分析和改进建议。",
)
async def code_review(code_review_request: CodeReviewRequest):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个资深 {language} 代码审查助手，帮助用户找出代码中的错误和改进建议。"),
        ("human", "请审查以下 {language} 代码，指出错误并给出改进建议：\n{code}"),
    ])
    chain = prompt | llm | StrOutputParser()
    result = await chain.ainvoke(code_review_request.model_dump())
    return {
        "language": code_review_request.language,
        "code": code_review_request.code,
        "review": result,
    }
