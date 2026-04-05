"""
扫雷游戏控制指令定义
"""
from __future__ import annotations

from lib_zmq_plugins.shared.base import BaseCommand


class NewGameCommand(BaseCommand, tag="new_game"):
    """新游戏指令"""
    rows: int = 16
    cols: int = 30
    mines: int = 99


COMMAND_TYPES = [
    NewGameCommand,
]