from .base import BaseEvent


class GameEndEvent(BaseEvent):
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
    is_official: int = 0
    is_fair: int = 0
    op: int = 0
    isl: int = 0
    pluck: float = 0
    raw_data: str = ''
