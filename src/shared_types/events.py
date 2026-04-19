"""
扫雷游戏事件类型定义
"""
from __future__ import annotations

from typing import List, Optional

from lib_zmq_plugins.shared.base import BaseEvent

from .enums import GameBoardState


class BoardUpdateEvent(BaseEvent, tag="board_update"):
    """
    棋盘更新事件 - 每次棋盘状态变化时发送

    Attributes:
        rows: 行数
        cols: 列数
        game_board: 游戏局面二维数组
            - 0-8: 已揭开的数字格子
            - 10: 未揭开的格子
            - 11: 标旗的格子
            - 14: 错误标旗（游戏结束时显示）
            - 15: 爆炸的地雷
            - 16: 未爆炸的地雷（游戏结束时显示）
        mines_remaining: 剩余未标出的地雷数（总地雷数 - 已标旗数）
        game_time: 游戏时间（秒）
    """
    rows: int = 0
    cols: int = 0
    game_board: List[List[int]] = []
    mines_remaining: int = 0
    game_time: float = 0.0


class GameStatusChangeEvent(BaseEvent, tag="game_status_change"):
    """
    游戏状态变化事件

    Attributes:
        last_status: 上一个游戏状态
        current_status: 当前游戏状态
    """
    last_status: int = 0
    current_status: int = 0


class ContextChangeEvent(BaseEvent, tag="context_change"):
    """上下文变化事件"""
    pass


class ButtonClickEvent(BaseEvent, tag="button_click"):
    """按钮点击事件"""
    col = 0
    row = 0
    button = 0


class VideoSaveEvent(BaseEvent, tag="video_save"):
    """录像保存事件"""

    game_board_state: int = 0
    rtime: float = 0
    left: int = 126
    right: int = 11
    double: int = 14
    left_s: float = 2.5583756345177666
    right_s: float = 0.2233502538071066
    double_s: float = 0.28426395939086296
    level: int = 5
    cl: int = 151
    cl_s: float = 3.065989847715736
    ce: int = 144
    ce_s: float = 2.9238578680203045
    rce: int = 11
    lce: int = 119
    dce: int = 14
    bbbv: int = 127
    bbbv_solved: int = 127
    bbbv_s: float = 2.5786802030456855
    flag: int = 11
    path: float = 6082.352554578606
    etime: float = 1666124184868000
    start_time: int = 1666124135606000
    end_time: int = 1666124184868000
    mode: int = 0
    software: str = "Arbiter"
    player_identifier: str = "Wang Jianing G01825"
    race_identifier: str = ""
    uniqueness_identifier: str = ""
    stnb: float = 0
    corr: float = 0
    thrp: float = 0
    ioe: float = 0
    is_official: bool = False
    is_fair: bool = False
    op: int = 0
    isl: int = 0
    pluck: float = 0
    raw_data: str = ""


EVENT_TYPES = [
    BoardUpdateEvent,
    GameStatusChangeEvent,
    ButtonClickEvent,
    VideoSaveEvent,
]
