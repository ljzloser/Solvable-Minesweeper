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


class MouseClickCommand(BaseCommand, tag="mouse_click"):
    """鼠标点击指令"""

    row: int = 0
    col: int = 0
    button: int = 0
    modifiers: int = 0


COMMAND_TYPES = [NewGameCommand, MouseClickCommand]
