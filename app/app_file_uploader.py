import time

import streamlit as st
from knowledge_base import KnowledgeBaseService

st.title('知识库')

upload_file = st.file_uploader(
    label='文件上传',
    type=['txt', 'text'],
    accept_multiple_files=False,
)

if "service" not in st.session_state:
    st.session_state.service = KnowledgeBaseService()

if upload_file is not None:
    file_name = upload_file.name
    file_type = upload_file.type
    file_size = upload_file.size / 1024

    st.subheader(f"文件名: {file_name}")
    st.write(f"格式:{file_type} , 大小:{file_size:.2f} KB")

    # getvalue -> byte -> str
    text = upload_file.getvalue().decode('utf-8')
    with st.spinner('正在加载向量数据库中...'):
        time.sleep(1)
        result = st.session_state.service.upload_by_str(text, file_name)
        st.write(result)
