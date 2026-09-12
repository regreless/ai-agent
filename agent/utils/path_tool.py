import os


# 获取 agent 目录，作为配置、提示词和日志的路径基准
def get_project_root() -> str:
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(current_dir)
    return project_root


# 相对路径 -> 绝对路径
def get_abs_path(relative_path: str) -> str:
    project_root = get_project_root()
    return os.path.join(project_root, relative_path)
