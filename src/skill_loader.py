"""读取 Markdown 技能，组装供模型使用的系统提示词。"""

import re
from dataclasses import dataclass
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent / ".dw" / "skills"


@dataclass
class Skill:
    name: str
    file_name: str
    description: str
    script: str
    examples: str = ""
    references: str = ""
    raw: str = ""


def parse_skill_file(file_path: str | Path) -> Skill:
    """读取单个技能文件，按 Markdown 标题解析并返回 Skill。

    一级标题作为技能名，缺失时使用文件名；二级标题对应各章节，缺失章节为空字符串。
    """
    file_path = Path(file_path)
    raw = file_path.read_text(encoding="utf-8-sig")
    name_match = re.search(r"^# (.+)$", raw, re.MULTILINE)
    parts = re.split(r"^## (.+)$", raw, flags=re.MULTILINE)
    # split 保留捕获的标题：奇数位置是标题，后面的偶数位置是正文。
    sections = {
        title.strip(): content.strip()
        for title, content in zip(parts[1::2], parts[2::2])
    }
    return Skill(
        name=name_match.group(1).strip() if name_match else file_path.name.removesuffix(".skill.md"),
        file_name=file_path.name,
        description=sections.get("Description", ""),
        script=sections.get("Script", ""),
        examples=sections.get("Examples", ""),
        references=sections.get("References", ""),
        raw=raw,
    )


def load_skills(skills_dir: str | Path = SKILLS_DIR) -> list[Skill]:
    """扫描指定目录的 .skill.md 文件，按文件名排序后返回技能列表。

    默认读取 src/.dw/skills，不递归扫描子目录；目录不存在或没有技能时返回空列表。
    """
    return [
        parse_skill_file(file_path)
        for file_path in sorted(Path(skills_dir).glob("*.skill.md"))
        if file_path.is_file()
    ]


def build_skills_prompt(skills: list[Skill]) -> str:
    """将技能列表拼成系统提示词，包含触发条件、执行步骤、示例和参考资料。

    跳过空章节；没有技能时返回空字符串。技能选择及步骤执行由模型根据提示词完成。
    """
    if not skills:
        return ""

    skill_blocks = []
    for skill in skills:
        sections = [f"### {skill.name}"]
        for section_name, content in (
            ("触发条件", skill.description),
            ("执行步骤", skill.script),
            ("示例", skill.examples),
            ("参考资料", skill.references),
        ):
            if content:
                sections.append(f"{section_name}：\n{content}")
        skill_blocks.append("\n\n".join(sections))

    return (
        "## 专项技能\n"
        "根据用户输入选择最匹配的技能，按照其执行步骤处理；没有匹配技能时正常回答。\n\n"
        + "\n\n".join(skill_blocks)
    )
