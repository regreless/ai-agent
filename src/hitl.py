"""人工确认：命中危险关键词时，在终端询问是否继续。"""

from dataclasses import dataclass, field

HIGH_RISK_KEYWORDS = [
    "rm -rf", "chmod 777", "sudo", "dd if=",
    "drop table", "drop database", "delete from", "truncate table",
    "删除所有", "清空数据库", "格式化", "删库", "强制删除",
]


@dataclass
class HitlConfig:
    enabled: bool = True
    extra_keywords: list[str] = field(default_factory=list)
    auto_approve: bool = False


def is_high_risk_operation(content: str, extra_keywords: list[str] | None = None) -> bool:
    """忽略大小写，检查是否包含内置或自定义危险关键词。"""
    keywords = HIGH_RISK_KEYWORDS + (extra_keywords or [])
    content = content.lower()
    return any(keyword.lower() in content for keyword in keywords)


def wait_for_confirmation(prompt: str = "请确认是否继续执行？(y/n): ") -> bool:
    """仅 y、yes 表示同意；其他输入、Ctrl+C 或输入结束均视为拒绝。"""
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def hitl_checkpoint(operation_desc: str, config: HitlConfig | None = None) -> bool:
    """执行前检查：返回 True 允许继续，False 表示取消。"""
    config = config or HitlConfig()
    if not config.enabled or not is_high_risk_operation(operation_desc, config.extra_keywords):
        return True

    print(f"\n[HITL] 检测到高风险操作：{operation_desc}")
    if config.auto_approve:
        print("[HITL] 自动批准，继续执行。")
        return True

    approved = wait_for_confirmation()
    print("[HITL] 已确认，继续执行。" if approved else "[HITL] 已拒绝，操作取消。")
    return approved
