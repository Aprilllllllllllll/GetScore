# -*- coding: utf-8 -*-
"""数据解析模块 — 原始 JSON → ScoreItem，挂科判断，学期解析"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

from src.models import ScoreItem, COURSE_TYPE_MAP

logger = logging.getLogger(__name__)

# 匹配课程名称中的编号前缀，如 "[15001161]毛泽东思想..." → ("15001161", "毛泽东思想...")
_COURSE_CODE_PATTERN: re.Pattern = re.compile(r"^\[([^\]]+)\](.*)$")

# 挂科/异常状态关键词
_FAIL_STATUSES = {"不及格", "缺考", "作弊", "取消资格", "违纪"}


def parse_course_name(raw_name: str) -> Tuple[str, str]:
    """从原始课程名称中提取编号和纯名称

    参数:
        raw_name: 如 "[15001161]毛泽东思想和中国特色社会主义理论体系概论"

    返回:
        (编号, 纯名称) 元组，如 ("15001161", "毛泽东思想...")
    """
    match = _COURSE_CODE_PATTERN.match(raw_name.strip())
    if match:
        return match.group(1), match.group(2).strip()
    return "", raw_name.strip()


def is_fail(item: Dict[str, Any]) -> bool:
    """判断一条成绩记录是否为挂科

    挂科规则（满足任一即为挂科）：
    1. 综合成绩 < 60（且为有效数字）
    2. 成绩状态在异常列表中（不及格/缺考/作弊等）
    3. 绩点为 0 且分数 < 60

    参数:
        item: 原始 API 返回的单条成绩数据

    返回:
        True 表示挂科
    """
    # 规则 2：状态判断（优先级最高，缺考/作弊等直接判定）
    status = item.get("tscjzwmc", "")
    if status in _FAIL_STATUSES:
        return True

    # 尝试解析分数
    raw_score = item.get("zhcj", "")
    score = _parse_score(raw_score)

    # 规则 1：分数 < 60
    if score is not None and score < 60:
        return True

    # 规则 3：绩点为 0 且分数 < 60
    grade_point = item.get("jd", 0)
    try:
        grade_point = float(grade_point)
    except (TypeError, ValueError):
        grade_point = 0
    if grade_point == 0 and score is not None and score < 60:
        return True

    return False


def _parse_score(raw_score: str) -> Optional[float]:
    """将字符串分数转为浮点数，无效时返回 None"""
    if not raw_score:
        return None
    raw_score = str(raw_score).strip()
    # 检查是否为有效数字（允许小数）
    if re.match(r"^\d+(\.\d+)?$", raw_score):
        return float(raw_score)
    return None


def parse_semester(xnxq: str) -> Tuple[str, str]:
    """从学期标识解析学年和学期

    参数:
        xnxq: 如 "2025-2026-2"

    返回:
        (学年, 学期名) 元组，如 ("2025-2026", "第二学期")
    """
    parts = xnxq.rsplit("-", 1)
    if len(parts) == 2:
        academic_year, term_code = parts
        term_name = "第一学期" if term_code == "1" else "第二学期"
        return academic_year, term_name
    # 兼容异常格式
    logger.warning(f"无法解析学期标识: {xnxq}")
    return xnxq, ""


def resolve_course_type(kcxz: str) -> str:
    """将课程性质编码转为中文名称

    参数:
        kcxz: 课程性质编码，如 "130"、"Z"

    返回:
        中文名称，未匹配时返回原始编码
    """
    if not kcxz:
        return "未知"
    return COURSE_TYPE_MAP.get(kcxz.strip(), kcxz)


def parse_score_item(raw: Dict[str, Any]) -> ScoreItem:
    """将 API 返回的原始 JSON 字典转换为 ScoreItem 对象

    参数:
        raw: API 返回的单条成绩数据

    返回:
        ScoreItem 实例
    """
    raw_name = raw.get("kcmc", "").strip()
    code, name = parse_course_name(raw_name)
    xnxq = raw.get("xnxq", "").strip()
    academic_year, term = parse_semester(xnxq)

    score = _parse_score(raw.get("zhcj", ""))

    # 处理绩点
    try:
        grade_point = float(raw.get("jd", 0))
    except (TypeError, ValueError):
        grade_point = 0.0

    # 处理学分
    try:
        credit = float(raw.get("xf", 0))
    except (TypeError, ValueError):
        credit = 0.0

    status = raw.get("tscjzwmc", "正常")

    # 处理补考/重修标记
    is_makeup = raw.get("sfbk", "0") not in ("0", "")
    is_retake = raw.get("sfcxxx", "0") not in ("0", "")

    course_type = resolve_course_type(raw.get("kcxz", ""))

    return ScoreItem(
        course_name=name,
        raw_course_code=code,
        course_type=course_type,
        score=score,
        grade_point=grade_point,
        credit=credit,
        semester=xnxq,
        academic_year=academic_year,
        term=term,
        status=status,
        is_fail=is_fail(raw),
        is_makeup=is_makeup,
        is_retake=is_retake,
    )


def compute_statistics(items: list) -> dict:
    """计算成绩统计概览

    参数:
        items: ScoreItem 列表

    返回:
        包含统计数据的字典
    """
    total = len(items)
    if total == 0:
        return {"total": 0}

    failed = sum(1 for item in items if item.is_fail)
    passed = total - failed
    valid_scores = [item.score for item in items if item.score is not None]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else None

    gpas = [item.grade_point for item in items if item.grade_point > 0]
    avg_gpa = sum(gpas) / len(gpas) if gpas else None

    total_credits = sum(item.credit for item in items)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "avg_score": round(avg_score, 2) if avg_score else None,
        "avg_gpa": round(avg_gpa, 2) if avg_gpa else None,
        "total_credits": round(total_credits, 1),
    }
