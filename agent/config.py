
api_key = "DEEPSEEK_API_KEY"
base_url = "https://api.deepseek.com"
model = "deepseek-v4-flash"


md5_path = './md5.txt'

zp_base_url = "https://open.bigmodel.cn/api/paas/v4/"
zp_model = "embedding-3"
zp_api_key = "1f7f94afb9b9402eb5d436471ea3c6d9.aMIvoIEUICm08ct2"

collection_name = 'rag'
persist_directory = './chroma_db'

chunk_size = 1000
chunk_overlap = 100
separators = ['\n\n', '\n', ',', '.', '?', '!', ' ', '']
max_split_char_number = 1000

similarity_threshold = 1