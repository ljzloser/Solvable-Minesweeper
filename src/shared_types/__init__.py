"""
共享类型模块

定义主进程和插件管理器共用的类型
"""
from .events import (
    BoardUpdateEvent,
    EVENT_TYPES,
)

from .commands import (
    NewGameCommand,
    COMMAND_TYPES,
)

__all__ = [
    # 事件
    "BoardUpdateEvent",
    "EVENT_TYPES",
    # 指令
    "NewGameCommand",
    "COMMAND_TYPES",
]
