#!/usr/bin/env python3
"""Any-Router 快捷启动脚本。

用法:
    python run.py "今天午饭花了38元"
    python run.py --report today
    python run.py --config
"""

import sys
import os

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from any_router.cli import main

main()
