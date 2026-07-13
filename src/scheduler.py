# -*- coding: utf-8 -*-
"""定时调度模块 — APScheduler 定时轮询成绩变化"""

import logging
import sys
import time
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import POLL_INTERVAL_MINUTES
from src.auth import login, verify_session, LoginError
from src.fetcher import fetch_all_scores, FetchError
from src.parser import parse_score_item, compute_statistics
from src.database import Database, DatabaseError
from src.notifier import notify_changes

logger = logging.getLogger(__name__)


def run_once(session=None, semester=None):
    """执行一次完整的查询-存储-通知流程

    参数:
        session: 可选的已有 session，不传则自动登录
        semester: 可选，指定学期如 "2025-2026-2"，不传则获取全部

    返回:
        (新增/变化数量, 挂科数量, 当前 session) 三元组
    """
    need_login = session is None

    if need_login:
        logger.info("=" * 50)
        logger.info(f"开始新一轮成绩检查 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)

        # 1. 登录
        try:
            session = login()
        except LoginError as e:
            logger.error(f"登录失败: {e}")
            return 0, 0, None
    else:
        # 检查已有 session 是否有效
        if not verify_session(session):
            logger.warning("Session 已过期，重新登录...")
            try:
                session = login()
            except LoginError as e:
                logger.error(f"重新登录失败: {e}")
                return 0, 0, None

    # 2. 抓取成绩
    try:
        raw_scores = fetch_all_scores(session, semester=semester)
    except FetchError as e:
        logger.error(f"成绩抓取失败: {e}")
        return 0, 0, session
    except Exception as e:
        logger.error(f"成绩抓取时发生未知错误: {e}")
        return 0, 0, session

    if not raw_scores:
        logger.info("未获取到任何成绩数据")
        return 0, 0, session

    # 3. 解析为结构化数据
    score_items = []
    for raw in raw_scores:
        try:
            item = parse_score_item(raw)
            score_items.append(item)
        except Exception as e:
            logger.warning(f"解析成绩数据时出错（已跳过）: {e}, 原始数据: {raw.get('kcmc', '未知')}")
            continue

    logger.info(f"成功解析 {len(score_items)} 条成绩")

    # 4. 统计概览
    stats = compute_statistics(score_items)
    logger.info(
        f"成绩概览: 共 {stats['total']} 门, "
        f"通过 {stats['passed']} 门, "
        f"挂科 {stats['failed']} 门, "
        f"平均分 {stats['avg_score']}, "
        f"平均绩点 {stats['avg_gpa']}"
    )

    # 5. 差异检测
    try:
        db = Database()
        changes = db.find_changes(score_items)
    except DatabaseError as e:
        logger.error(f"数据库操作失败: {e}")
        return 0, 0, session

    # 6. 如果有变化，存储并通知
    new_or_updated = 0
    fail_count = 0
    if changes:
        logger.info(f"检测到 {len(changes)} 条成绩变化")
        for change in changes:
            try:
                db.upsert(change.item)
                new_or_updated += 1
                if change.item.is_fail:
                    fail_count += 1
            except DatabaseError as e:
                logger.error(f"存储成绩失败: {e}")

        # 推送通知
        notify_changes(changes)
    else:
        logger.info("无新增或变化的成绩")

    logger.info(
        f"本轮检查完成 — "
        f"新增/更新 {new_or_updated} 条, 挂科 {fail_count} 门"
    )
    return new_or_updated, fail_count, session


def start_scheduler():
    """启动定时调度器，按配置间隔轮询成绩

    使用 APScheduler BlockingScheduler，每 POLL_INTERVAL_MINUTES 分钟执行一次。
    此函数会阻塞当前线程，直到收到 SIGINT/SIGTERM。
    """
    logger.info(f"定时调度器启动，轮询间隔: {POLL_INTERVAL_MINUTES} 分钟")
    logger.info("按 Ctrl+C 停止")

    # 首次立即执行
    logger.info("执行首次成绩查询...")
    session = None
    try:
        session = login()
        _, _, session = run_once(session=session)
    except Exception as e:
        logger.error(f"首次查询失败: {e}")

    # 定时任务
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    @scheduler.scheduled_job(
        IntervalTrigger(minutes=POLL_INTERVAL_MINUTES),
        id="score_poll",
        name="成绩轮询任务",
        misfire_grace_time=60,  # 错过 60 秒内仍然执行
    )
    def poll_job():
        """定时轮询任务"""
        nonlocal session
        try:
            _, _, session = run_once(session=session)
        except Exception as e:
            logger.error(f"轮询任务执行异常: {e}", exc_info=True)
            # 异常时重置 session，下次重新登录
            session = None

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("收到停止信号，调度器正在退出...")
        scheduler.shutdown(wait=False)
        logger.info("调度器已停止")
