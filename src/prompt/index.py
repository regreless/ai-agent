from langchain_core.prompts import PromptTemplate
import os
from langchain_openai import ChatOpenAI
import config.index as config

llm = ChatOpenAI(
    model=config.model,
    api_key=os.environ.get(config.api_key),
    base_url=config.base_url,
    extra_body={"thinking": {"type": "disabled"}},
)

pro_temp = PromptTemplate.from_template("我的一个远方的朋友，他喜欢打篮球，给他起个外号{nickname}，简单回答")


# 原始方案
# pro_text = pro_temp.format(nickname='死亡缠绕')
# res = llm.invoke(pro_text)
# print(res.content)

# chain 调用
chain = pro_temp | llm
res  = chain.invoke(input="死亡缠绕")
print(res.content)