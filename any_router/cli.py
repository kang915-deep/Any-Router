"""CLI 命令行界面 — Any-Router 的用户交互入口。"""

import sys

from any_router import __app_name__, __version__
from any_router.actions.accounting import AccountingHandler, ReportHandler
from any_router.config import Settings
from any_router.console import (
    print_error,
    print_info,
    print_panel,
    print_result,
    print_status,
    print_table,
    print_warning,
)
from any_router.engine import parse
from any_router.exceptions import (
    AnyRouterError,
    UnknownActionError,
    ValidationError,
)
from any_router.router import Router
from any_router.storage.sqlite_store import SQLiteStore


def _init_router() -> Router:
    """初始化路由器和各处理器。"""
    settings = Settings()
    settings.validate()

    store = SQLiteStore(settings.DB_PATH)
    router = Router()
    router.register("accounting", AccountingHandler(store))
    router.register("report", ReportHandler(store))
    return router


def _cmd_record(user_input: str) -> None:
    """处理单条自然语言输入。"""
    router = _init_router()

    print_status("正在理解您的输入...")
    intent = parse(user_input)

    action = intent.get("action", "")

    # 将原始输入传递给 handler 用于分类猜测
    params = intent.get("params", {})
    if isinstance(params, dict):
        params["_raw_input"] = user_input

    print_status("正在处理...")
    result = router.dispatch(action, params)

    print_result(result)


def _cmd_report(period: str) -> None:
    """查询统计报表。"""
    router = _init_router()

    print_status("正在生成报表...")
    result = router.dispatch("report", {"period": period})

    print_result(result)


def _cmd_config() -> None:
    """查看当前配置。"""
    try:
        cfg = Settings.print_config()
    except Exception:
        cfg = {"error": "配置加载失败"}

    label_map = {
        "api_key": "API Key",
        "base_url": "API 地址",
        "model": "模型",
        "db_path": "数据库路径",
    }

    rows = []
    for key, value in cfg.items():
        label = label_map.get(key, key)
        rows.append([label, str(value)])

    print_table("Any-Router 配置", ["配置项", "值"], rows)


def _cmd_categories() -> None:
    """查看分类列表。"""
    try:
        settings = Settings()
        store = SQLiteStore(settings.DB_PATH)
    except Exception as e:
        print_error(f"加载失败: {e}")
        return

    cats = store.get_all_categories()

    rows = []
    for c in cats:
        type_label = "支出" if c["type"] == "expense" else "收入"
        alias = c["aliases"] or "-"
        rows.append([type_label, c["name"], alias])

    print_table("记账分类", ["类型", "分类名", "别名"], rows)


def main() -> None:
    """CLI 主入口。"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="any-router",
        description=f"{__app_name__} v{__version__} - 极简个人意图路由与自动化 Agent",
        epilog="示例: any-router \"今天午饭花了38元\"",
    )

    parser.add_argument(
        "input",
        nargs="?",
        help='自然语言输入，如 "今天午饭花了38元"',
    )
    parser.add_argument(
        "--report",
        metavar="PERIOD",
        nargs="?",
        const="this-month",
        choices=["today", "yesterday", "this-week", "this-month", "last-month"],
        help="查询统计报表 (today/yesterday/this-week/this-month/last-month)",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="查看当前配置",
    )
    parser.add_argument(
        "--categories",
        action="store_true",
        help="查看分类列表",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本号",
    )

    args = parser.parse_args()

    # ── 版本号 ──
    if args.version:
        print(f"{__app_name__} v{__version__}")
        return

    # ── 查看配置 ──
    if args.config:
        _cmd_config()
        return

    # ── 查看分类 ──
    if args.categories:
        _cmd_categories()
        return

    # ── 查询报表 ──
    if args.report:
        _cmd_report(args.report)
        return

    # ── 自然语言记账 ──
    if args.input:
        try:
            _cmd_record(args.input)
        except ValidationError as e:
            print_warning(str(e))
            sys.exit(1)
        except UnknownActionError as e:
            print_warning(str(e))
            sys.exit(1)
        except AnyRouterError as e:
            print_error(str(e))
            sys.exit(1)
        return

    # ── 无参数，显示帮助 ──
    parser.print_help()
    print("")
    print_panel(
        "提示: 试试: any-router \"今天午饭花了38元\"\n"
        "       any-router --report today",
        "cyan",
    )


if __name__ == "__main__":
    main()
