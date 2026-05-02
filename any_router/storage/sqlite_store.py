"""SQLite 持久化存储 — 记账数据管理。"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from any_router.exceptions import DatabaseError


class SQLiteStore:
    """SQLite 存储层，管理 transactions 和 categories 表。"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    # ── 数据库初始化 ──────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接。"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        except sqlite3.Error as e:
            raise DatabaseError(f"无法打开数据库: {e}")

    def _init_db(self) -> None:
        """初始化数据表。"""
        try:
            with self._get_conn() as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS categories (
                        name        TEXT PRIMARY KEY,
                        type        TEXT NOT NULL CHECK(type IN ('expense', 'income')),
                        aliases     TEXT NOT NULL DEFAULT ''
                    );

                    CREATE TABLE IF NOT EXISTS transactions (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        type        TEXT NOT NULL CHECK(type IN ('expense', 'income')),
                        amount      REAL NOT NULL CHECK(amount > 0),
                        category    TEXT NOT NULL,
                        note        TEXT NOT NULL DEFAULT '',
                        created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                    );

                    -- 默认分类
                    INSERT OR IGNORE INTO categories VALUES ('餐饮', 'expense', '吃饭,午餐,晚餐,早餐,外卖,咖啡,奶茶');
                    INSERT OR IGNORE INTO categories VALUES ('交通', 'expense', '打车,地铁,公交,加油,停车');
                    INSERT OR IGNORE INTO categories VALUES ('购物', 'expense', '网购,超市,日用品,衣服');
                    INSERT OR IGNORE INTO categories VALUES ('日用', 'expense', '水电,物业,话费,网费');
                    INSERT OR IGNORE INTO categories VALUES ('娱乐', 'expense', '电影,游戏,旅游,健身');
                    INSERT OR IGNORE INTO categories VALUES ('医疗', 'expense', '看病,药,体检');
                    INSERT OR IGNORE INTO categories VALUES ('其他支出', 'expense', '');
                    INSERT OR IGNORE INTO categories VALUES ('工资', 'income', '薪资,薪水,收入');
                    INSERT OR IGNORE INTO categories VALUES ('其他收入', 'income', '红包,退款,理财');
                """)
        except sqlite3.Error as e:
            raise DatabaseError(f"初始化数据库失败: {e}")

    # ── 分类查询 ──────────────────────────────────────────────

    def get_all_categories(self, type_filter: Optional[str] = None) -> list[dict]:
        """获取分类列表。"""
        with self._get_conn() as conn:
            if type_filter:
                rows = conn.execute(
                    "SELECT * FROM categories WHERE type = ? ORDER BY name",
                    (type_filter,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM categories ORDER BY type, name"
                ).fetchall()
            return [dict(r) for r in rows]

    def resolve_category(self, raw_text: str, tx_type: str) -> str:
        """根据输入文本和类型，自动匹配预定义分类。"""
        text_lower = raw_text.lower()
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT name, aliases FROM categories WHERE type = ?", (tx_type,)
            ).fetchall()
            for row in rows:
                name = row["name"]
                aliases = row["aliases"]
                # 检查输入是否包含分类名或别名
                if name.lower() in text_lower:
                    return name
                for alias in aliases.split(","):
                    alias = alias.strip().lower()
                    if alias and alias in text_lower:
                        return name
        # 未能匹配，返回默认分类
        default = "餐饮" if tx_type == "expense" else "其他收入"
        return default

    # ── 交易操作 ──────────────────────────────────────────────

    def add_transaction(
        self,
        tx_type: str,
        amount: float,
        category: str,
        note: str = "",
        created_at: Optional[str] = None,
    ) -> int:
        """添加一笔交易记录。

        Returns:
            新记录的自增 ID。
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO transactions (type, amount, category, note, created_at)
                   VALUES (?, ?, ?, ?, COALESCE(?, datetime('now', 'localtime')))""",
                (tx_type, amount, category, note, created_at),
            )
            return cursor.lastrowid

    def get_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        type_filter: Optional[str] = None,
        days: Optional[int] = None,
    ) -> list[dict]:
        """查询交易记录。"""
        conditions = []
        params = []

        if type_filter:
            conditions.append("type = ?")
            params.append(type_filter)
        if days is not None:
            since = (datetime.now() - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            conditions.append("created_at >= ?")
            params.append(since)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM transactions {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_summary(
        self,
        days: Optional[int] = None,
        type_filter: Optional[str] = None,
    ) -> dict:
        """获取统计摘要。"""
        conditions = []
        params = []

        if type_filter:
            conditions.append("type = ?")
            params.append(type_filter)
        if days is not None:
            since = (datetime.now() - timedelta(days=days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            conditions.append("created_at >= ?")
            params.append(since)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        with self._get_conn() as conn:
            # 总计
            row = conn.execute(
                f"""
                SELECT
                    COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) as total_expense,
                    COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) as total_income,
                    COUNT(*) as count
                FROM transactions {where}
                """,
                params,
            ).fetchone()

            # 分类汇总
            cat_rows = conn.execute(
                f"""
                SELECT type, category, SUM(amount) as total, COUNT(*) as count
                FROM transactions {where}
                GROUP BY type, category
                ORDER BY total DESC
                """,
                params,
            ).fetchall()

            result = dict(row)
            result["categories"] = [dict(r) for r in cat_rows]
            return result
