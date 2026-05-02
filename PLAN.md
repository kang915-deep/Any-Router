# Any-Router 项目实施计划

> 基于 [项目文档.md](./项目文档.md) 的需求描述，制定可落地的分阶段实施方案。
> 当前聚焦 **Phase 1**：CLI 命令行工具 + 记账功能。

---

## 一、总体架构

```
用户输入 (CLI 命令行)
    │
    ▼
Any-Router CLI (any_router/cli.py)
    │
    ▼
意图解析引擎 (any_router/engine.py)
    │  ┌──────────────────────────────┐
    │  │ POST DeepSeek-V4 Chat API    │
    │  │ model: deepseek-chat         │
    │  │ response_format: json_object │
    │  │ System Prompt (~150 tokens)  │
    │  └──────────────────────────────┘
    │
    ▼
JSON 结构化意图  ← 例如: {"action":"accounting","params":{...}}
    │
    ▼
路由器 (any_router/router.py)
    │
    ├──→ Action: accounting → AccountingHandler
    │       └── 存储到 SQLite (any_router/storage/sqlite_store.py)
    │
    ├──→ Action: query → QueryHandler (计划 Phase 2)
    │
    └──→ Action: calendar | todo | smart_home (计划 Phase 2+)
```

---

## 二、Phase 1 — 核心实现（当前阶段）

### 2.1 项目结构

```
any-router/
├── any_router/
│   ├── __init__.py
│   ├── cli.py                 # CLI 入口 (ArgumentParser + Rich 美化输出)
│   ├── engine.py              # 意图解析引擎 (DeepSeek-V4 API 调用)
│   ├── router.py              # 路由分发器 (Action → Handler 映射)
│   ├── config.py              # 配置管理 (dotenv + 配置文件)
│   ├── exceptions.py          # 自定义异常
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── base.py            # ActionHandler 抽象基类
│   │   └── accounting.py      # 记账 Action 处理器
│   └── storage/
│       ├── __init__.py
│       └── sqlite_store.py    # SQLite 持久化存储
├── tests/
│   ├── test_engine.py
│   ├── test_router.py
│   └── test_accounting.py
├── pyproject.toml             # 项目元信息 + 依赖管理
├── .env.example               # 环境变量模板
├── 项目文档.md                 # 已有项目说明文档
└── PLAN.md                    # 本实施计划
```

### 2.2 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.8+ | 跨平台，生态丰富 |
| API 客户端 | `httpx` | 异步 HTTP 客户端，支持流式 |
| CLI | `argparse` + `rich` | 标准库参数解析 + 美化的控制台输出 |
| 存储 | `sqlite3` (内置库) | 零依赖，轻量可靠 |
| 配置 | `python-dotenv` | 管理 API Key 等敏感信息 |
| 包管理 | `uv` 或 `pip` | 现代 Python 项目管理 |

### 2.3 关键设计

#### (1) System Prompt — 极致精简 (< 150 Tokens)

```
你是意图路由器。将用户输入解析为 JSON。
可用操作: accounting(记账)

记账参数:
  type: "expense"(支出) | "income"(收入)
  amount: 金额(数字)
  category: 分类(如 餐饮/交通/购物/日用/其他)
  note: 备注(可选)
  time: 时间(ISO 8601, 可选, 默认当前时间)

仅输出 JSON，不要额外文字。
```

#### (2) SQLite 数据模型

```sql
CREATE TABLE transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL CHECK(type IN ('expense', 'income')),
    amount      REAL    NOT NULL CHECK(amount > 0),
    category    TEXT    NOT NULL,
    note        TEXT    DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE categories (
    name        TEXT PRIMARY KEY,
    type        TEXT    NOT NULL CHECK(type IN ('expense', 'income')),
    aliases     TEXT    DEFAULT ''  -- 逗号分隔的同义词
);
```

#### (3) CLI 界面设计

```bash
# 记账模式 — 自然语言输入，一步完成
any-router "今天午饭花了38元"
# → ✅ 已记录：支出 38.00 元 | 餐饮 | 今天午饭

any-router "收到工资15000"
# → ✅ 已记录：收入 15000.00 元 | 工资

any-router "打车去机场花了180"
# → ✅ 已记录：支出 180.00 元 | 交通 | 打车去机场

# 查询模式
any-router --report today
any-router --report this-month
any-router --report "2026-04"

# 交互模式 (可选)
any-router --interactive
> 今天午饭花了38元
> ✅ 已记录...
> 咖啡25
> ✅ 已记录...
> /report
> 📊 本月支出汇总...
> /exit
```

### 2.4 处理流程（完整链路）

```
1. 用户输入 "今天午饭花了38元"
2. CLI 接收输入，传给 Engine.parse()
3. Engine 构建 System Prompt + 用户输入，调 DeepSeek-V4 API
4. API 返回 {"action":"accounting","params":{"type":"expense","amount":38,"category":"餐饮","note":"今天午饭"}}
5. Router 匹配 action="accounting"，分发给 AccountingHandler
6. AccountingHandler 校验参数合法性（金额>0、分类有效等）
7. 调用 SQLiteStore 写入数据库
8. 返回格式化结果给 CLI
9. CLI 输出 "✅ 已记录：支出 38.00 元 | 餐饮 | 今天午饭"
```

### 2.5 依赖清单 (`pyproject.toml`)

```toml
[project]
name = "any-router"
version = "0.1.0"
description = "极简个人意图路由与自动化 Agent"
requires-python = ">=3.8"
dependencies = [
    "httpx>=0.25",
    "python-dotenv>=1.0",
    "rich>=13.0",
]

[project.scripts]
any-router = "any_router.cli:main"
```

---

## 三、Phase 2 — 扩展功能（后续阶段）

### 3.1 更多 Action

| Action | 功能 | 集成方向 |
|--------|------|----------|
| `calendar` | 日程管理 | CalDAV / Google Calendar API |
| `todo` | 待办管理 | Todoist / Notion API |
| `smart_home` | 智能家居 | HomeAssistant API / 米家 |
| `query` | 查询统计 | 基于已存数据的报表查询 |

### 3.2 更多输入方式

| 方式 | 说明 |
|------|------|
| 微信机器人 | 接入 WeChat API / 微信个人号协议，发消息即记账 |
| 语音输入 | 通过 ASR（如讯飞/Whisper）转文字后输入引擎 |
| HTTP API | 启动 Web 服务，对外提供 REST API |

### 3.3 能力增强

- **多轮消歧**：当 AI 无法确定参数时，支持追问补全
- **分类自动学习**：根据历史输入，自动对未识别的分类进行归类建议
- **报表能力**：按日/周/月/年生成支出统计报表

---

## 四、里程碑与任务拆解

### Milestone 1: 项目骨架 (Day 1)
- [x] 项目文档 (已完成)
- [ ] 创建 `pyproject.toml`，声明依赖
- [ ] 创建 `any_router/` 包结构
- [ ] 实现 `config.py` — 环境变量加载
- [ ] 创建 `.env.example` 和 `.gitignore`

### Milestone 2: 核心引擎 (Day 1-2)
- [ ] 实现 `engine.py` — DeepSeek-V4 API 调用 + System Prompt
- [ ] 实现 `exceptions.py` — 自定义异常
- [ ] 编写单元测试 (mock API 调用)

### Milestone 3: 路由与存储 (Day 2)
- [ ] 实现 `storage/sqlite_store.py` — 数据库初始化、CRUD、查询
- [ ] 实现 `actions/base.py` — ActionHandler 抽象基类
- [ ] 实现 `router.py` — 路由分发器
- [ ] 编写单元测试

### Milestone 4: 记账 Action (Day 2-3)
- [ ] 实现 `actions/accounting.py` — 支出/收入记录、分类管理
- [ ] 实现参数校验逻辑
- [ ] 编写单元测试

### Milestone 5: CLI 界面 (Day 3)
- [ ] 实现 `cli.py` — 参数解析 + Rich 美化输出
- [ ] 实现 `--report` 统计查询功能
- [ ] 端到端集成测试

### Milestone 6: 完善与文档 (Day 3-4)
- [ ] 添加详细注释和使用说明
- [ ] 提供分类配置文件示例
- [ ] 实现 `--interactive` 交互模式 (可选)
- [ ] 验证整体流程，修复边界情况

---

## 五、基本原则

1. **极致精简**：保持 System Prompt < 150 Tokens，运行时依赖不超过 3 个
2. **Json Only**：强制 `json_object` 模式，所有 AI 输出必须可解析为 JSON
3. **无状态**：每次请求独立，不携带历史上下文
4. **先核心再扩展**：Phase 1 聚焦 CLI + 记账，Phase 2 逐步扩展
5. **可测试**：核心逻辑均有单元测试覆盖

---

*计划版本: v1.0 | 更新日期: 2026-05-02*
