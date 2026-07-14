# -*- coding: utf-8 -*-
"""成绩查看模块 — 将本地已存储的成绩格式化为易读的表格输出"""

import unicodedata
from typing import Optional

from src.database import Database
from src.config import DB_PATH

_TABLE_WIDTH = 62
_NAME_WIDTH = 30


def _str_width(s: str) -> int:
    """计算字符串的显示宽度（中日韩全角字符按 2 计算）"""
    width = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def _pad(s: str, width: int) -> str:
    """按显示宽度（非字符数）右侧补齐空格，兼容中英文混排对齐"""
    s = str(s)
    fill = width - _str_width(s)
    if fill <= 0:
        return s
    return s + " " * fill


def _truncate(s: str, width: int) -> str:
    """按显示宽度截断字符串，超长时以 … 结尾，保证表格列对齐"""
    s = str(s)
    if _str_width(s) <= width:
        return s
    out = []
    w = 0
    for ch in s:
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if w + cw > width - 1:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


def _fmt_num(value) -> str:
    """格式化数字 — 整数不显示小数位，小数保留 1 位"""
    if value is None:
        return "-"
    value = float(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def _fmt_score(score, status: str) -> str:
    """格式化成绩显示 — 无有效分数时显示状态文字"""
    if score is None:
        return status or "-"
    return _fmt_num(score)


def print_scores(semester: Optional[str] = None) -> None:
    """打印格式化的成绩表格，按学期分组展示，并附带统计信息

    参数:
        semester: 可选，仅显示指定学期（如 "2025-2026-2"），不传则显示全部
    """
    if not DB_PATH.exists():
        print("📭 未找到成绩数据库，请先执行查询: python main.py once")
        return

    db = Database()
    rows = db.get_all(semester=semester)

    if not rows:
        if semester:
            print(f"📭 学期 {semester} 暂无成绩数据")
        else:
            print("📭 暂无成绩数据，请先执行查询: python main.py once")
        return

    # 按学期分组，保持数据库返回的顺序（学期降序）
    groups = {}
    order = []
    for r in rows:
        key = r["semester"]
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(r)

    # ---- 总览 ----
    total = len(rows)
    total_credits = sum(r["credit"] for r in rows)
    valid_scores = [r["score"] for r in rows if r["score"] is not None]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else None
    gpas = [r["grade_point"] for r in rows if r["grade_point"] > 0]
    avg_gpa = sum(gpas) / len(gpas) if gpas else None
    fail_rows = [r for r in rows if r["is_fail"]]

    print("=" * _TABLE_WIDTH)
    summary = f" 📊 成绩总览 — 共 {total} 门课程 | 学分 {_fmt_num(total_credits)}"
    if avg_score is not None:
        summary += f" | 平均分 {avg_score:.2f}"
    if avg_gpa is not None:
        summary += f" | 平均绩点 {avg_gpa:.2f}"
    if fail_rows:
        summary += f" | ⚠️ 挂科 {len(fail_rows)} 门"
    print(summary)
    print("=" * _TABLE_WIDTH)

    # ---- 分学期明细 ----
    for key in order:
        items = groups[key]
        academic_year = items[0]["academic_year"] or key
        term = items[0]["term"]
        credits = sum(i["credit"] for i in items)
        scores = [i["score"] for i in items if i["score"] is not None]
        avg = sum(scores) / len(scores) if scores else None
        gps = [i["grade_point"] for i in items if i["grade_point"] > 0]
        gpa = sum(gps) / len(gps) if gps else None
        failed = sum(1 for i in items if i["is_fail"])

        header = f"\n▶ {academic_year} {term}（{len(items)} 门 | 学分 {_fmt_num(credits)}"
        if avg is not None:
            header += f" | 平均分 {avg:.2f}"
        if gpa is not None:
            header += f" | 平均绩点 {gpa:.2f}"
        header += f" | 挂科 {failed} 门）" if failed else "）"
        print(header)
        print("-" * _TABLE_WIDTH)
        print(
            f"  {_pad('ID', 4)}{_pad('课程名称', _NAME_WIDTH)}"
            f"{_pad('成绩', 6)}{_pad('绩点', 5)}{_pad('学分', 5)} 状态"
        )
        for i in items:
            score_str = _fmt_score(i["score"], i["status"])
            flag = "❌" if i["is_fail"] else "✅"
            name = _truncate(i["course_name"], _NAME_WIDTH)
            print(
                f"  {_pad(i['id'], 4)}{_pad(name, _NAME_WIDTH)}"
                f"{_pad(score_str, 6)}{_pad(_fmt_num(i['grade_point']), 5)}"
                f"{_pad(_fmt_num(i['credit']), 5)} {flag} {i['status']}"
            )

    # ---- 挂科汇总 ----
    if fail_rows:
        print(f"\n⚠️  挂科/异常课程汇总（{len(fail_rows)} 门）:")
        for r in fail_rows:
            score_str = _fmt_score(r["score"], r["status"])
            print(f"  - {r['course_name']} ({r['semester']}): {score_str}")

    print()
