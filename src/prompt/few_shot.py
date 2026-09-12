from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate
import os
from langchain_openai import ChatOpenAI
import config.index as config

example_template = PromptTemplate.from_template("单词{word}，反义词{antonym}")

# list套dict 动态
examples_data = [
    {"word": "大", "antonym": "小"},
    {"word": "左", "antonym": "右"}
]

llm = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

few_shot_template = FewShotPromptTemplate(
    example_prompt=example_template,
    examples=examples_data,
    prefix="告知我单词的反义词，这是提供的示例",
    suffix="基于前面的示例，{input_word}的反义词是？",
    input_variables=["input_word"]
)

prompt_text = few_shot_template.invoke(input={"input_word": "上"}).to_string()

print(prompt_text)

print(llm.invoke(prompt_text).content)
