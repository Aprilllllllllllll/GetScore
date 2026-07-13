# -*- coding: utf-8 -*-
"""配置管理 — 从 .env 文件和系统环境变量读取配置"""

import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 加载 .env 文件
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file)
else:
    # 尝试从 .env.example 加载（但不含真实密码，仅用于测试通知功能）
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env.example")
    logging.warning(".env 文件不存在，使用 .env.example 作为模板，请创建真实的 .env 文件")


def _env(name: str, default: str = "") -> str:
    """读取环境变量，去除首尾空白"""
    return os.getenv(name, default).strip()


# ---- 登录相关 ----
STUDENT_ID: str = _env("STUDENT_ID")
PASSWORD: str = _env("PASSWORD")
RSA_PUBLIC_KEY: str = _env(
    "RSA_PUBLIC_KEY",
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCs9/40OodE8Nf63Qs6x5wsoj2o"
    "CSaI09c8gRbQLR3us3R63DtDgvZ0LZcFqQhfRvhM/w6f/LPPEAudT78QYV1p0JlF"
    "MYEUNgNjKq2Q8xAz6c2Lis8PtE5pa6BG9wLCG4CMdSZiu/pnDcZCB8Imis8ywBFP"
    "uN24txwsaUrZtpedVwIDAQAB",
)

# ---- 通知相关 ----
SERVER_CHAN_KEY: str = _env("SERVER_CHAN_KEY")

# ---- 轮询相关 ----
POLL_INTERVAL_MINUTES: int = int(_env("POLL_INTERVAL_MINUTES", "30"))

# ---- 路径相关 ----
DATA_DIR: Path = PROJECT_ROOT / "data"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
DB_PATH: Path = DATA_DIR / "scores.db"
LOG_FILE: Path = LOGS_DIR / "app.log"

# ---- 教务系统 URL ----
CAS_LOGIN_URL: str = (
    "https://sso.gxnu.edu.cn/cas/login"
    "?service=https://jwjx.gxnu.edu.cn/jw/admin/caslogin"
)
SCORE_API_URL: str = (
    "https://jwjx.gxnu.edu.cn/jw/admin/xsd/xsdcjcx/xsdQueryXscjList"
)

# ---- HTTP 请求配置 ----
HTTP_HEADERS: dict = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://jwjx.gxnu.edu.cn/",
}
REQUEST_TIMEOUT: int = 30          # 请求超时（秒）
MAX_RETRIES: int = 3               # 最大重试次数
RETRY_DELAY: int = 2               # 重试等待（秒）

# ---- 分页配置 ----
PAGE_ROWS: int = 200               # 每页抓取条数（设大以减少请求次数）


def validate_config() -> list:
    """校验必要配置是否完整，返回缺失项列表"""
    missing = []
    if not STUDENT_ID:
        missing.append("STUDENT_ID（学号）")
    if not PASSWORD:
        missing.append("PASSWORD（密码）")
    return missing
