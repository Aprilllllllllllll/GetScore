# -*- coding: utf-8 -*-
"""SQLite 数据库操作模块 — 成绩的增删改查与差异检测"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from src.models import ScoreItem, ScoreChange
from src.config import DB_PATH, DATA_DIR

logger = logging.getLogger(__name__)

# 数据库唯一键格式：{raw_course_code}:{semester}
_UNIQUE_KEY = "raw_course_code || ':' || semester"

# 建表 SQL
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name     TEXT    NOT NULL,
    raw_course_code TEXT    NOT NULL DEFAULT '',
    course_type     TEXT    NOT NULL DEFAULT '',
    semester        TEXT    NOT NULL DEFAULT '',
    academic_year   TEXT    NOT NULL DEFAULT '',
    term            TEXT    NOT NULL DEFAULT '',
    credit          REAL    NOT NULL DEFAULT 0,
    score           REAL,
    grade_point     REAL    NOT NULL DEFAULT 0,
    status          TEXT    NOT NULL DEFAULT '正常',
    is_fail         INTEGER NOT NULL DEFAULT 0,
    is_makeup       INTEGER NOT NULL DEFAULT 0,
    is_retake       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT '',
    updated_at      TEXT    NOT NULL DEFAULT '',
    UNIQUE(raw_course_code, semester)
)
"""


class DatabaseError(Exception):
    """数据库操作异常"""
    pass


class Database:
    """成绩数据库管理类"""

    def __init__(self, db_path: Path = None):
        """初始化数据库连接

        参数:
            db_path: SQLite 文件路径（Path 或 str），默认使用配置中的 DB_PATH
        """
        if db_path is None:
            self._db_path = DB_PATH
        elif isinstance(db_path, str):
            self._db_path = Path(db_path)
        else:
            self._db_path = db_path
        self._ensure_data_dir()
        self._init_db()

    def _ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        """初始化数据库表结构"""
        try:
            conn = self._get_conn()
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()
            conn.close()
            logger.info(f"数据库已就绪: {self._db_path}")
        except Exception as e:
            raise DatabaseError(f"数据库初始化失败: {e}")

    def get_all_as_dict(self) -> Dict[str, dict]:
        """获取所有成绩，以唯一键索引

        返回:
            {(课程编号:学期): {字段字典}} 的映射
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM scores ORDER BY semester DESC, raw_course_code"
            ).fetchall()
            result = {}
            for row in rows:
                d = dict(row)
                key = f"{d['raw_course_code']}:{d['semester']}"
                result[key] = d
            return result
        except Exception as e:
            raise DatabaseError(f"查询成绩失败: {e}")
        finally:
            conn.close()

    def get_all(self, semester: Optional[str] = None) -> List[dict]:
        """获取所有成绩记录（列表形式，可选按学期过滤）

        参数:
            semester: 可选，指定学期如 "2025-2026-2"，不传则返回全部

        返回:
            成绩记录字典列表，按学期降序、ID 升序排列
        """
        conn = self._get_conn()
        try:
            if semester:
                rows = conn.execute(
                    "SELECT * FROM scores WHERE semester = ? ORDER BY semester DESC, id",
                    (semester,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM scores ORDER BY semester DESC, id"
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            raise DatabaseError(f"查询成绩失败: {e}")
        finally:
            conn.close()

    def upsert(self, item: ScoreItem) -> bool:
        """插入或更新一条成绩记录

        按 (raw_course_code, semester) 复合唯一键判断是否已存在。
        已存在且分数/绩点/状态有变化时更新，无变化则跳过。

        参数:
            item: ScoreItem 实例

        返回:
            True 表示有新插入或数据更新
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT id, score, grade_point, status, is_fail, is_makeup, is_retake "
                "FROM scores WHERE raw_course_code = ? AND semester = ?",
                (item.raw_course_code, item.semester),
            )
            existing = cursor.fetchone()

            if existing is None:
                # 新记录 — 插入
                conn.execute(
                    """
                    INSERT INTO scores (
                        course_name, raw_course_code, course_type,
                        semester, academic_year, term,
                        credit, score, grade_point, status,
                        is_fail, is_makeup, is_retake,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.course_name, item.raw_course_code, item.course_type,
                        item.semester, item.academic_year, item.term,
                        item.credit, item.score, item.grade_point, item.status,
                        int(item.is_fail), int(item.is_makeup), int(item.is_retake),
                        now, now,
                    ),
                )
                conn.commit()
                logger.info(f"新增成绩: {item.course_name} ({item.semester}) 分数={item.score}")
                return True
            else:
                # 已存在 — 检查关键字段是否有变化
                changed = (
                    existing["score"] != item.score
                    or existing["grade_point"] != item.grade_point
                    or existing["status"] != item.status
                    or bool(existing["is_fail"]) != item.is_fail
                    or bool(existing["is_makeup"]) != item.is_makeup
                    or bool(existing["is_retake"]) != item.is_retake
                )
                if changed:
                    conn.execute(
                        """
                        UPDATE scores SET
                            course_name=?, course_type=?, academic_year=?, term=?,
                            credit=?, score=?, grade_point=?, status=?,
                            is_fail=?, is_makeup=?, is_retake=?,
                            updated_at=?
                        WHERE id=?
                        """,
                        (
                            item.course_name, item.course_type,
                            item.academic_year, item.term,
                            item.credit, item.score, item.grade_point,
                            item.status,
                            int(item.is_fail), int(item.is_makeup), int(item.is_retake),
                            now,
                            existing["id"],
                        ),
                    )
                    conn.commit()
                    old_score = existing["score"]
                    logger.info(
                        f"成绩更新: {item.course_name} ({item.semester}) "
                        f"{old_score} → {item.score}"
                    )
                    return True
                else:
                    logger.debug(f"成绩无变化，跳过: {item.course_name} ({item.semester})")
                    return False
        except Exception as e:
            raise DatabaseError(f"写入成绩失败 ({item.course_name}): {e}")
        finally:
            conn.close()

    def find_changes(self, items: List[ScoreItem]) -> List[ScoreChange]:
        """与数据库对比，找出新增或变化的成绩

        参数:
            items: 新抓取的 ScoreItem 列表

        返回:
            ScoreChange 列表（仅包含有变化的条目）
        """
        stored = self.get_all_as_dict()
        changes: List[ScoreChange] = []

        for item in items:
            key = f"{item.raw_course_code}:{item.semester}"
            if key not in stored:
                changes.append(ScoreChange(item=item, change_type="新增"))
            elif stored[key]["score"] != item.score:
                changes.append(ScoreChange(
                    item=item,
                    change_type="更新",
                    old_score=stored[key]["score"],
                ))

        return changes

    def get_statistics(self) -> dict:
        """获取全局统计信息，按学年学期分组"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT
                    academic_year, term,
                    COUNT(*) AS total,
                    SUM(CASE WHEN is_fail = 0 THEN 1 ELSE 0 END) AS passed,
                    SUM(CASE WHEN is_fail = 1 THEN 1 ELSE 0 END) AS failed,
                    SUM(credit) AS total_credits,
                    AVG(CASE WHEN score IS NOT NULL THEN score END) AS avg_score,
                    AVG(CASE WHEN grade_point > 0 THEN grade_point END) AS avg_gpa
                FROM scores
                GROUP BY academic_year, term
                ORDER BY academic_year DESC, term DESC
                """
            ).fetchall()

            result = {}
            for row in rows:
                d = dict(row)
                key = f"{d['academic_year']} {d['term']}"
                result[key] = {
                    "total": d["total"],
                    "passed": d["passed"],
                    "failed": d["failed"],
                    "total_credits": round(d["total_credits"], 1) if d["total_credits"] else 0,
                    "avg_score": round(d["avg_score"], 2) if d["avg_score"] else None,
                    "avg_gpa": round(d["avg_gpa"], 2) if d["avg_gpa"] else None,
                }
            return result
        except Exception as e:
            raise DatabaseError(f"查询统计失败: {e}")
        finally:
            conn.close()
