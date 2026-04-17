"""
扫雷游戏控制指令定义
"""
from __future__ import annotations

from typing import Optional

from lib_zmq_plugins.shared.base import BaseCommand

from .enums import GameLevel


class NewGameCommand(BaseCommand, tag="new_game"):
    """
    新游戏指令
    
    Attributes:
        level: 游戏难度，使用 GameLevel 枚举值
            - 3: 初级 (8x8, 10雷)
            - 4: 中级 (16x16, 40雷)
            - 5: 高级 (16x30, 99雷)
            - 6: 自定义（使用 rows/cols/mines）
        rows: 行数（自定义模式时使用）
        cols: 列数（自定义模式时使用）
        mines: 地雷数（自定义模式时使用）
    """
    level: int = 6  # 默认自定义，使用 rows/cols/mines
    rows: int = 16
    cols: int = 30
    mines: int = 99


class MouseClickCommand(BaseCommand, tag="mouse_click"):
    """
    鼠标点击指令
    
    Attributes:
        row: 行索引（从 0 开始）
        col: 列索引（从 0 开始）
        button: 鼠标按钮
            - 0: 左键（揭开格子）
            - 1: 中键
            - 2: 右键（标旗）
        modifiers: 键盘修饰符（保留）
    """
    row: int = 0
    col: int = 0
    button: int = 0
    modifiers: int = 0


COMMAND_TYPES = [NewGameCommand, MouseClickCommand]