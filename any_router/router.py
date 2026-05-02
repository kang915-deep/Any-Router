"""路由分发器 — 将解析后的意图分发给对应的 Action 处理器。"""

from typing import Any

from any_router.actions.base import ActionHandler
from any_router.exceptions import UnknownActionError


class Router:
    """根据 action 类型分发到对应的 Handler。"""

    def __init__(self):
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, action: str, handler: ActionHandler) -> None:
        """注册一个 Action 处理器。

        Args:
            action: Action 名称（如 "accounting"）。
            handler: 对应的处理器实例。
        """
        self._handlers[action] = handler

    def dispatch(self, action: str, params: dict[str, Any]) -> str:
        """分发意图到对应的处理器。

        Args:
            action: 意图中的 action 字段。
            params: 意图中的 params 字段。

        Returns:
            处理结果字符串。

        Raises:
            UnknownActionError: 未注册的 action 类型。
        """
        handler = self._handlers.get(action)
        if handler is None:
            raise UnknownActionError(
                f"未知操作: '{action}'。"
                f"当前支持的操作: {', '.join(self._handlers.keys())}"
            )
        return handler.handle(params)
