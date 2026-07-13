# -*- coding: utf-8 -*-
"""成绩查询系统 — 主入口

用法:
    python main.py once      单次查询成绩并推送通知
    python main.py schedule  启动定时轮询（后台持续运行）
    python main.py test      测试通知推送通道
"""

import logging
import sys
import os
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import LOGS_DIR, LOG_FILE
from src.config import validate_config


def setup_logging():
    """配置日志系统 — 同时输出到控制台和文件"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Windows 控制台 UTF-8 兼容处理
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    # 日志格式
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 控制台 handler（INFO 及以上）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    root_logger.addHandler(console_handler)

    # 文件 handler（DEBUG 及以上，完整日志）
    file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root_logger.addHandler(file_handler)

    # 降低第三方库日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


def print_banner():
    """打印启动横幅"""
    banner = r"""
  ╔══════════════════════════════════════╗
  ║        📚 成绩查询与监控系统         ║
  ║     广西师范大学 · GetScore v1.0     ║
  ╚══════════════════════════════════════╝
"""
    print(banner)


def cmd_once():
    """单次查询模式"""
    from src.scheduler import run_once

    print_banner()
    missing = validate_config()
    if missing:
        print(f"❌ 缺少必要配置项: {', '.join(missing)}")
        print("请编辑 .env 文件后重试（可参考 .env.example）")
        sys.exit(1)

    # 解析 --semester 参数
    semester = _parse_semester_arg()

    try:
        new_count, fail_count, _ = run_once(semester=semester)
        if new_count == 0:
            print("✅ 无新增成绩变化")
        else:
            print(f"✅ 查询完成 — 新增/更新 {new_count} 条，挂科 {fail_count} 门")
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        sys.exit(1)


def cmd_schedule():
    """定时轮询模式"""
    from src.scheduler import start_scheduler

    print_banner()
    missing = validate_config()
    if missing:
        print(f"❌ 缺少必要配置项: {', '.join(missing)}")
        print("请编辑 .env 文件后重试（可参考 .env.example）")
        sys.exit(1)

    print(f"📋 日志文件: {LOG_FILE}")
    print(f"⏱️  按 Ctrl+C 停止\n")
    start_scheduler()


def cmd_test():
    """测试通知推送通道"""
    from src.notifier import send_test_notification

    print_banner()
    print("🔔 正在测试通知推送通道...\n")

    result = send_test_notification()
    if result:
        print("✅ 测试通知发送成功！")
    else:
        print("❌ 测试通知发送失败，请检查配置")


def _parse_semester_arg():
    """从命令行参数中提取 --semester 值"""
    for i, arg in enumerate(sys.argv):
        if arg == "--semester" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if arg.startswith("--semester="):
            return arg.split("=", 1)[1]
    return None


def print_usage():
    """打印使用说明"""
    print_banner()
    print("用法:")
    print("  python main.py once                         单次查询全部学期成绩")
    print("  python main.py once --semester 2025-2026-2  单次查询指定学期成绩")
    print("  python main.py schedule                     启动定时轮询（全部学期）")
    print("  python main.py test                         测试通知推送通道")
    print("")
    print("学期格式: 2025-2026-1（第一学期）或 2025-2026-2（第二学期）")
    print("首次使用请先复制 .env.example 为 .env 并填入真实学号和密码")


def main():
    """主函数"""
    logger = setup_logging()

    # 解析命令
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    cmd = sys.argv[1].lower()

    commands = {
        "once": cmd_once,
        "schedule": cmd_schedule,
        "test": cmd_test,
        "help": print_usage,
        "--help": print_usage,
        "-h": print_usage,
    }

    handler = commands.get(cmd)
    if handler:
        handler()
    else:
        print(f"❌ 未知命令: {cmd}\n")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
