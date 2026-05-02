"""轻量级控制台输出工具 — 替代 Rich，仅使用标准库。"""

import shutil
from typing import Optional


def _term_width() -> int:
    """获取终端宽度。"""
    return shutil.get_terminal_size().columns


def _color(text: str, color_code: str) -> str:
    """ANSI 颜色包裹。"""
    return f"{color_code}{text}\033[0m"


# ANSI 颜色常量
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"


def print_success(text: str) -> None:
    """绿色成功信息。"""
    print(_color(text, GREEN))


def print_error(text: str) -> None:
    """红色错误信息。"""
    print(_color(f"[ERR] {text}", RED))


def print_warning(text: str) -> None:
    """黄色警告信息。"""
    print(_color(f"[WRN] {text}", YELLOW))


def print_info(text: str) -> None:
    """蓝色信息。"""
    print(_color(text, CYAN))


def print_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    """打印简易表格。"""
    width = _term_width()
    print("")
    print(_color(f" {title} ", BOLD))
    print(_color("-" * min(width, 60), DIM))

    # 计算列宽
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    # 表头
    header_line = "  "
    for i, h in enumerate(headers):
        header_line += _color(h.ljust(col_widths[i]), BOLD + CYAN) + "  "
    print(header_line)
    print(_color("  " + "  ".join(["-" * w for w in col_widths]), DIM))

    # 行
    for row in rows:
        line = "  "
        for i, cell in enumerate(row):
            if i < len(col_widths):
                line += cell.ljust(col_widths[i]) + "  "
        print(line)

    print(_color("-" * min(width, 60), DIM))


def print_panel(text: str, border_color: str = "cyan") -> None:
    """带边框的面板。"""
    lines = text.split("\n")
    width = min(max(len(l) for l in lines) + 4, _term_width() - 2)
    border = "-" * width
    color_map = {"cyan": CYAN, "green": GREEN, "blue": BLUE, "red": RED}
    c = color_map.get(border_color, CYAN)
    print(_color(f"+{border}+", c))
    for line in lines:
        print(_color(f"| {line.ljust(width - 2)} |", c))
    print(_color(f"+{border}+", c))


def print_status(text: str) -> None:
    """状态提示。"""
    print(_color(f"... {text}", DIM))


def print_result(result: str) -> None:
    """展示处理结果。"""
    if "\n" in result:
        print_panel(result, "cyan")
    else:
        print_success(result)
