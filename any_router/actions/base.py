"""Action 处理器抽象基类。"""

from abc import ABC, abstractmethod
from typing import Any


class ActionHandler(ABC):
    """所有 Action 处理器的基类。"""

    @abstractmethod
    def handle(self, params: dict[str, Any]) -> str:
        """处理解析后的意图参数，返回用户可读的结果信息。

        Args:
            params: 意图解析后的参数字典。

        Returns:
            格式化后的结果字符串，直接展示给用户。
        """
        ...
