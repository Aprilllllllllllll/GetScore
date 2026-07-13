# -*- coding: utf-8 -*-
"""成绩数据抓取模块 — 分页遍历成绩 API，返回原始 JSON 数据"""

import logging
import time
from typing import List, Dict, Any, Optional

import requests

from src.config import (
    SCORE_API_URL,
    HTTP_HEADERS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    PAGE_ROWS,
)

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """数据抓取异常"""
    pass


def fetch_all_scores(
    session: requests.Session,
    semester: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """分页抓取成绩数据

    参数:
        session: 已登录的 requests.Session 实例
        semester: 可选，指定学期筛选，如 "2025-2026-2"。不传则获取全部学期。

    返回:
        成绩数据列表，每条为原始 JSON 字典

    异常:
        FetchError: 抓取过程失败
    """
    all_results: List[Dict[str, Any]] = []
    page = 1

    semester_label = f"学期 {semester}" if semester else "全部学期"
    logger.info(f"开始抓取成绩数据（{semester_label}）...")

    while True:
        params = {
            "fxbz": "0",
            "gridtype": "jqgrid",
            "page": page,
            "rows": PAGE_ROWS,
        }
        if semester:
            params["xnxq"] = semester

        # 带重试的请求
        data = None
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = session.get(
                    SCORE_API_URL,
                    params=params,
                    headers=HTTP_HEADERS,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.encoding = "utf-8"

                if resp.status_code != 200:
                    raise FetchError(
                        f"第 {page} 页请求失败，HTTP {resp.status_code}"
                    )

                data = resp.json()
                break
            except FetchError:
                raise
            except Exception as e:
                last_error = e
                logger.warning(
                    f"第 {page} 页请求失败（第 {attempt}/{MAX_RETRIES} 次尝试）: {e}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)

        if data is None:
            raise FetchError(
                f"第 {page} 页抓取失败，已重试 {MAX_RETRIES} 次。"
                f"最后错误: {last_error}"
            )

        # 检查返回码
        ret_code = data.get("ret", -1)
        if ret_code != 0:
            error_msg = data.get("msg", "未知错误")
            raise FetchError(f"API 返回错误 (ret={ret_code}): {error_msg}")

        # 提取本页数据
        page_results = data.get("results", [])
        if not page_results and page == 1:
            logger.warning("未找到任何成绩数据，可能本学期暂未出成绩")
            return []

        all_results.extend(page_results)

        total_pages = data.get("totalPages", 1)
        total_records = data.get("total", len(all_results))

        logger.info(
            f"第 {page}/{total_pages} 页，"
            f"本页 {len(page_results)} 条，共 {total_records} 条"
        )

        if page >= total_pages:
            break

        page += 1
        # 分页间隔，避免请求过快
        time.sleep(0.5)

    logger.info(f"成绩抓取完成，共获取 {len(all_results)} 条记录")
    return all_results
