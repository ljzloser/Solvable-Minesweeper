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


class GameEndEvent(BaseEvent, tag="game_end"):
    """
    游戏结束事件。发生在游戏胜利、失败、重开、游戏关闭、游戏设置关闭、切换游戏状态关闭、
    游戏状态变为非正式等情况。
    playing状态切换为其他状态时触发此消息。自定义难度、各种模式均会触发。
    """

    # 游戏的新状态（旧状态必为playing），'ready'、'study'、'show'、'playing'、'joking'、
    # 'fail'、'win'、'jofail'、'jowin'、'display'、'showdisplay'分别记作0-10
    game_state: int = 0
    # False-flag, True-nf
    nf: bool = False
    row: int = 16
    column: int = 30
    mine_num: int = 99
    rtime: float = 0.0
    left: int = 126
    right: int = 11
    double: int = 14
    # 游戏难度（级别）。3是初级；4是中级；5是高级；6是自定义。
    level: int = 5
    cl: int = 151
    ce: int = 144
    rce: int = 11
    lce: int = 119
    dce: int = 14
    bbbv: int = 127
    bbbv_solved: int = 127
    zini: int = 105
    flag: int = 11
    path: float = 6082.352554578606
    # 时间戳，微秒
    start_time: int = 1666124135606000
    end_time: int = 1666124184868000
    # 标准0、win74、经典无猜5、强无猜6、弱无猜7、准无猜8、强可猜9、弱可猜10
    mode: int = 0
    software: str = "元 3.2.2"
    player_identifier: str = "Wang Jianing"
    race_identifier: str = "G1234"
    uniqueness_identifier: str = ""
    is_official: bool = False
    is_fair: bool = False
    op: int = 0
    isl: int = 0
    pluck: float = 0
    board: List[List[int]] = []
    # evf4版本的二进制数据
    raw_data: bytes = b""


EVENT_TYPES = [
    BoardUpdateEvent,
    GameStatusChangeEvent,
    ButtonClickEvent,
    GameEndEvent,
]
