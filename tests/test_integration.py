"""集成测试 — 不依赖 DeepSeek API 的完整链路验证。"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import requests


def _mock_deepseek_response(user_input: str) -> dict:
    """模拟 DeepSeek API 的返回结果。"""
    # 根据输入模拟不同的意图识别结果
    mock_responses = {
        "午饭": {
            "action": "accounting",
            "params": {
                "type": "expense",
                "amount": 38,
                "category": "餐饮",
                "note": "今天午饭",
            },
        },
        "打车": {
            "action": "accounting",
            "params": {
                "type": "expense",
                "amount": 25,
                "category": "交通",
                "note": "打车去公司",
            },
        },
        "工资": {
            "action": "accounting",
            "params": {
                "type": "income",
                "amount": 15000,
                "category": "工资",
                "note": "5月工资",
            },
        },
        "咖啡": {
            "action": "accounting",
            "params": {
                "type": "expense",
                "amount": 32,
                "category": "餐饮",
                "note": "咖啡",
            },
        },
    }

    for keyword, response in mock_responses.items():
        if keyword in user_input:
            return response

    # 默认返回
    return {
        "action": "accounting",
        "params": {
            "type": "expense",
            "amount": 100,
            "category": "其他支出",
            "note": user_input,
        },
    }


def mock_post(*args, **kwargs):
    """模拟 requests.post 返回。"""

    class MockResponse:
        def __init__(self, data):
            self.status_code = 200
            self._data = data

        def json(self):
            return self._data

        @property
        def text(self):
            return json.dumps(self._data)

    # 从请求体中提取用户输入
    body = kwargs.get("json", {})
    messages = body.get("messages", [])
    user_msg = ""
    for msg in messages:
        if msg["role"] == "user":
            user_msg = msg["content"]
            break

    intent = _mock_deepseek_response(user_msg)
    return MockResponse(
        {
            "choices": [{"message": {"content": json.dumps(intent, ensure_ascii=False)}}]
        }
    )


def test_full_pipeline():
    """测试完整流水线：CLI 输入 → 解析 → 路由 → 存储 → 输出。"""
    # 使用临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    from any_router.config import Settings

    # 临时覆盖配置
    original_db_path = Settings.DB_PATH
    Settings.DB_PATH = db_path

    from any_router.storage.sqlite_store import SQLiteStore
    from any_router.actions.accounting import AccountingHandler, ReportHandler

    store = SQLiteStore(db_path)
    handler = AccountingHandler(store)
    report_handler = ReportHandler(store)

    # ── 测试 1: 记录支出 ──
    with patch.object(requests, "post", mock_post):
        from any_router.engine import parse

        intent = parse("今天午饭花了38元")
        assert intent["action"] == "accounting"
        assert intent["params"]["amount"] == 38

        result = handler.handle(intent["params"])
        assert "已记录" in result
        assert "38" in result
        assert "餐饮" in result
        assert "支出" in result
        print(f"[PASS] 测试1 - 记录支出: {result}")

    # ── 测试 2: 记录收入 ──
    with patch.object(requests, "post", mock_post):
        intent = parse("收到工资15000")
        result = handler.handle(intent["params"])
        assert "已记录" in result
        assert "15000" in result
        assert "工资" in result
        assert "收入" in result
        print(f"[PASS] 测试2 - 记录收入: {result}")

    # ── 测试 3: 自动分类匹配 ──
    with patch.object(requests, "post", mock_post):
        intent = parse("打车去机场花了25")
        result = handler.handle(intent["params"])
        assert "交通" in result
        print(f"[PASS] 测试3 - 自动分类: {result}")

    # ── 测试 4: 统计报表 ──
    report = report_handler.handle({"period": "this-month"})
    assert "财务摘要" in report
    assert "总支出" in report
    assert "总收入" in report
    # 我们插入了 38 + 25 = 63 支出, 15000 收入
    assert "63" in report.replace(",", "")
    assert "15000" in report
    print(f"[PASS] 测试4 - 统计报表")

    # ── 测试 5: 参数校验 ──
    try:
        handler.handle({"type": "expense", "amount": -10, "category": "餐饮"})
        assert False, "应抛出 ValidationError"
    except Exception as e:
        assert "金额" in str(e)
        print(f"[PASS] 测试5 - 负数金额校验")

    try:
        handler.handle({"type": "unknown_type", "amount": 100, "category": "餐饮"})
        assert False, "应抛出 ValidationError"
    except Exception as e:
        assert "类型" in str(e)
        print(f"[PASS] 测试6 - 无效类型校验")

    # ── 测试 7: 查询单个交易 ──
    txs = store.get_transactions(limit=10)
    assert len(txs) >= 2
    print(f"[PASS] 测试7 - 交易查询: {len(txs)} 条记录")

    # 清理
    Settings.DB_PATH = original_db_path
    db_path.unlink()
    print("\n✅ 所有集成测试通过!")


if __name__ == "__main__":
    test_full_pipeline()
