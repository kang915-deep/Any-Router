"""Any-Router 自定义异常。"""


class AnyRouterError(Exception):
    """所有 Any-Router 异常的基类。"""


class ConfigError(AnyRouterError):
    """配置错误（如缺少 API Key）。"""


class APIConnectionError(AnyRouterError):
    """API 连接失败。"""


class APIResponseError(AnyRouterError):
    """API 返回异常（如 HTTP 错误、响应格式错误）。"""


class ParsingError(AnyRouterError):
    """AI 返回的 JSON 无法正确解析。"""


class ValidationError(AnyRouterError):
    """参数校验失败。"""


class DatabaseError(AnyRouterError):
    """数据库操作失败。"""


class UnknownActionError(AnyRouterError):
    """未知的 Action 类型。"""
