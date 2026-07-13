# -*- coding: utf-8 -*-
"""数据类型定义 — 成绩相关的强类型数据结构"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class ScoreItem:
    """单条成绩的完整数据模型"""
    # 课程信息
    course_name: str                        # 课程纯名称（去除编号）
    raw_course_code: str                    # 原始课程编号，如 [15001161]
    course_type: str                        # 课程性质，如"公共必修课"

    # 成绩数据
    score: Optional[float] = None           # 综合成绩（缺考/作弊时为 None）
    grade_point: float = 0.0                # 绩点
    credit: float = 0.0                     # 学分

    # 学期信息
    semester: str = ""                      # 原始学期标识，如 "2025-2026-2"
    academic_year: str = ""                 # 学年，如 "2025-2026"
    term: str = ""                          # 学期，如 "第二学期"

    # 状态标记
    status: str = "正常"                    # 成绩状态：正常/不及格/缺考/作弊
    is_fail: bool = False                   # 是否挂科

    # 补考信息
    is_makeup: bool = False                 # 是否补考成绩
    is_retake: bool = False                 # 是否重修成绩

    # 元数据
    created_at: str = ""                    # 首次入库时间
    updated_at: str = ""                    # 最后更新时间


@dataclass
class ScoreChange:
    """成绩变化记录 — 用于差异检测和通知"""
    item: ScoreItem                         # 变化后的成绩数据
    change_type: str                        # "新增" 或 "更新"
    old_score: Optional[float] = None       # 变化前的分数（仅更新时有值）


@dataclass
class SemesterStats:
    """按学期的统计信息"""
    academic_year: str                      # 学年
    term: str                               # 学期
    total_courses: int = 0                  # 课程总数
    total_credits: float = 0.0              # 总学分
    passed_courses: int = 0                 # 通过课程数
    failed_courses: int = 0                 # 挂科课程数
    avg_score: Optional[float] = None       # 平均分
    avg_gpa: Optional[float] = None         # 平均绩点
    gpa_sum: float = 0.0                    # 绩点总和（内部计算用）
    valid_score_count: int = 0              # 有效成绩课程数（排除缺考等）


# 课程性质编码 → 中文名称映射表
COURSE_TYPE_MAP: Dict[str, str] = {
    "130": "公共必修课",
    "120": "公共选修课",
    "Z": "专业必修课",
    "X": "专业选修课",
    "S": "实践教学课",
    "T": "通识选修课",
    "G": "公共基础课",
}
