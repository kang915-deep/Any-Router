"""记账 Action 处理器 — 处理支出/收入的记录与查询。"""

from typing import Any

from any_router.actions.base import ActionHandler
from any_router.exceptions import ValidationError
from any_router.storage.sqlite_store import SQLiteStore


class AccountingHandler(ActionHandler):
    """处理 accounting 类型的意图，执行记账操作。"""

    # 有效分类类型
    VALID_TYPES = ("expense", "income")
    # 类型中文映射
    TYPE_LABELS = {"expense": "支出", "income": "收入"}

    def __init__(self, store: SQLiteStore):
        self.store = store

    def _validate(self, params: dict[str, Any]) -> dict[str, Any]:
        """校验并规范化参数。"""
        # 兼容处理：确保从 params 中获取 type 时不会因 None 值崩溃
        raw_type = params.get("type")
        tx_type = str(raw_type or "").lower().strip()

        # 智能补全：如果 AI 没给 type，尝试从原始输入中根据关键词猜测
        if not tx_type:
            raw_input = params.get("_raw_input", "")
            expense_keywords = ("花", "买", "支出", "付费", "扣款", "支付")
            income_keywords = ("收", "赚", "工资", "奖金", "入账", "红包")
            
            if any(k in raw_input for k in expense_keywords):
                tx_type = "expense"
            elif any(k in raw_input for k in income_keywords):
                tx_type = "income"

        if tx_type not in self.VALID_TYPES:
            raise ValidationError(
                f"无法确定交易类型 (支出/收入)。请尝试更明确的表达，如 '花了...' 或 '收到...'。\n"
                f"(DEBUG: AI 返回的类型为 '{raw_type}')"
            )

        try:
            amount = float(params.get("amount", 0))
        except (TypeError, ValueError):
            raise ValidationError(f"无效的金额: '{params.get('amount')}'")

        if amount <= 0:
            raise ValidationError(f"金额必须大于 0，收到: {amount}")

        if amount > 99999999:
            raise ValidationError(f"金额过大，请检查输入: {amount}")

        category = params.get("category", "")
        if not category or not category.strip():
            # 自动从输入原文猜测分类
            category = self.store.resolve_category(
                params.get("_raw_input", ""), tx_type
            )
        category = category.strip()

        note = str(params.get("note", "")).strip()
        time = params.get("time")
        if not time or not str(time).strip():
            time = None  # 确保空字符串传给数据库时能触发 COALESCE 默认值

        return {
            "type": tx_type,
            "amount": amount,
            "category": category,
            "note": note,
            "time": time,
        }

    def handle(self, params: dict[str, Any]) -> str:
        """执行记账操作。"""
        validated = self._validate(params)

        tx_id = self.store.add_transaction(
            tx_type=validated["type"],
            amount=validated["amount"],
            category=validated["category"],
            note=validated["note"],
            created_at=validated["time"],
        )

        type_label = self.TYPE_LABELS[validated["type"]]
        amount_str = f"{validated['amount']:.2f}"

        parts = [f"[SUCCESS] 已记录：{type_label} {amount_str} 元"]
        parts.append(validated["category"])
        if validated["note"]:
            parts.append(validated["note"])

        return " | ".join(parts)


class ReportHandler(ActionHandler):
    """处理 report 查询请求。"""

    PERIOD_LABELS = {
        "today": "今天",
        "yesterday": "昨天",
        "this-week": "本周",
        "this-month": "本月",
        "last-month": "上个月",
    }

    PERIOD_DAYS = {
        "today": 1,
        "yesterday": 2,
        "this-week": 7,
        "this-month": 30,
        "last-month": 60,
    }

    def __init__(self, store: SQLiteStore):
        self.store = store

    def handle(self, params: dict[str, Any]) -> str:
        period = params.get("period", "this-month")
        days = self.PERIOD_DAYS.get(period, 30)
        label = self.PERIOD_LABELS.get(period, period)

        summary = self.store.get_summary(days=days)

        lines = [f"[REPORT] {label} 财务摘要"]
        lines.append(f"   总支出: {summary['total_expense']:.2f} 元")
        lines.append(f"   总收入: {summary['total_income']:.2f} 元")
        lines.append(f"   交易笔数: {summary['count']}")

        if summary["categories"]:
            lines.append("")
            lines.append("  按分类:")
            for cat in summary["categories"]:
                t_label = "支出" if cat["type"] == "expense" else "收入"
                lines.append(
                    f"    {t_label} - {cat['category']}: {cat['total']:.2f} 元 ({cat['count']}笔)"
                )

        return "\n".join(lines)
