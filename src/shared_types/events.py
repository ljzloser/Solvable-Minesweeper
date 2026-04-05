"""
扫雷游戏事件类型定义
"""
from __future__ import annotations

from lib_zmq_plugins.shared.base import BaseEvent


class GameStartedEvent(BaseEvent, tag="game_started"):
    """游戏开始事件"""
    rows: int = 0
    cols: int = 0
    mines: int = 0


class GameEndedEvent(BaseEvent, tag="game_ended"):
    """游戏结束事件"""
    is_win: bool = False
    time: float = 0.0


class BoardUpdateEvent(BaseEvent, tag="board_update"):
    """局面刷新事件"""
    board: list[list[int]] = []


EVENT_TYPES = [
    GameStartedEvent,
    GameEndedEvent,
    BoardUpdateEvent,
]