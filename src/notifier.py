# -*- coding: utf-8 -*-
"""消息推送模块 — 支持 Server酱、控制台输出"""

import logging
from typing import List

import requests

from src.models import ScoreChange
from src.config import SERVER_CHAN_KEY, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def build_message(changes: List[ScoreChange]) -> str:
    """构建推送消息文本

    参数:
        changes: 成绩变化列表

    返回:
        格式化的消息文本
    """
    if not changes:
        return ""

    total = len(changes)
    new_count = sum(1 for c in changes if c.change_type == "新增")
    update_count = sum(1 for c in changes if c.change_type == "更新")
    fail_count = sum(1 for c in changes if c.item.is_fail)

    lines = [
        f"📚 成绩更新通知",
        f"共 {total} 条变化（新增 {new_count} 条，更新 {update_count} 条）",
    ]

    if fail_count > 0:
        lines.append(f"⚠️ 挂科/异常 {fail_count} 门，请注意！")

    lines.append("")

    # 挂科项优先展示
    fail_items = [c for c in changes if c.item.is_fail]
    normal_items = [c for c in changes if not c.item.is_fail]

    if fail_items:
        lines.append("━━━ 挂科/异常 ━━━")
        for c in fail_items:
            score_str = f"{c.item.score}分" if c.item.score is not None else c.item.status
            old_info = ""
            if c.change_type == "更新" and c.old_score is not None:
                old_info = f"（原 {c.old_score} 分）"
            lines.append(
                f"❌ [{c.change_type}] {c.item.course_name}"
            )
            lines.append(
                f"   学年: {c.item.academic_year} {c.item.term} | "
                f"成绩: {score_str} | 绩点: {c.item.grade_point} | "
                f"状态: {c.item.status}{old_info}"
            )

    if normal_items:
        lines.append("━━━ 正常成绩 ━━━")
        for c in normal_items:
            score_str = f"{c.item.score}分" if c.item.score is not None else c.item.status
            old_info = ""
            if c.change_type == "更新" and c.old_score is not None:
                old_info = f"（原 {c.old_score} 分）"
            lines.append(
                f"✅ [{c.change_type}] {c.item.course_name}"
            )
            lines.append(
                f"   学年: {c.item.academic_year} {c.item.term} | "
                f"成绩: {score_str} | 绩点: {c.item.grade_point} | "
                f"学分: {c.item.credit}{old_info}"
            )

    return "\n".join(lines)


def send_via_server_chan(title: str, content: str) -> bool:
    """通过 Server酱 Turbo 版发送推送

    参数:
        title: 消息标题
        content: 消息正文（支持 Markdown）

    返回:
        True 表示发送成功
    """
    if not SERVER_CHAN_KEY:
        logger.debug("未配置 SERVER_CHAN_KEY，跳过 Server酱推送")
        return False

    url = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"
    payload = {
        "title": title,
        "desp": content,
    }
    try:
        resp = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT)
        resp.encoding = "utf-8"
        result = resp.json()
        if result.get("code") == 0:
            logger.info("Server酱推送成功")
            return True
        else:
            logger.warning(f"Server酱推送失败: {result.get('message', '未知错误')}")
            return False
    except Exception as e:
        logger.error(f"Server酱推送异常: {e}")
        return False


def notify_changes(
    changes: List[ScoreChange],
    silent_if_empty: bool = True,
) -> str:
    """统一的成绩变化通知入口

    推送策略：
    1. 配置了 Server酱 → 优先通过 Server酱推送
    2. 未配置 → 仅控制台输出
    3. silent_if_empty=True 时，无变化不推送

    参数:
        changes: 成绩变化列表
        silent_if_empty: 无变化时是否静默

    返回:
        生成的消息文本（可能为空）
    """
    if not changes and silent_if_empty:
        return ""

    message = build_message(changes)

    if not message:
        return ""

    # 控制台输出（始终执行）
    print("\n" + "=" * 50)
    print(message)
    print("=" * 50 + "\n")

    # Server酱推送
    if SERVER_CHAN_KEY:
        total = len(changes)
        fail_count = sum(1 for c in changes if c.item.is_fail)
        title_parts = [f"📚 成绩更新 ({total}条)"]
        if fail_count > 0:
            title_parts.append(f"⚠️挂科{fail_count}门")
        title = " ".join(title_parts)

        # 转换为 HTML 格式以适应 Server酱
        html_content = message.replace("\n", "<br>")
        send_via_server_chan(title, html_content)

    return message


def send_test_notification() -> bool:
    """发送测试通知，验证推送通道是否正常

    返回:
        True 表示推送成功
    """
    test_content = (
        "📚 成绩查询系统 — 测试通知\n\n"
        "如果你收到此消息，说明推送通道配置正确！\n"
        "系统将在检测到成绩变化时自动推送通知。\n\n"
        f"当前时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("\n" + "=" * 50)
    print(test_content)
    print("=" * 50 + "\n")

    if SERVER_CHAN_KEY:
        html_content = test_content.replace("\n", "<br>")
        return send_via_server_chan("成绩查询系统 — 测试通知", html_content)
    else:
        logger.info("未配置 SERVER_CHAN_KEY，仅输出了测试消息到控制台")
        return True  # 控制台输出也算成功
