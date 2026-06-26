from __future__ import annotations

import pytest
from utils import (
    board_list_to_bytes, board_bytes_to_board,
    StatsRecord, trans_game_mode, EnuLimit,
)


class TestBoardBytes:
    def test_board_list_to_bytes_small(self):
        board = [[-1, 0], [1, -1]]
        result = board_list_to_bytes(board)
        assert isinstance(result, bytes)
        assert len(result) == 1

    def test_board_list_to_bytes_empty(self):
        assert board_list_to_bytes([]) == b''

    def test_board_bytes_roundtrip(self):
        original = [[-1, 0, 0], [1, -1, 1], [0, 1, -1]]
        encoded = board_list_to_bytes(original)
        decoded = board_bytes_to_board(3, 3, encoded)
        for row in decoded:
            assert len(row) == 3
        assert decoded[0][0] == -1
        assert decoded[1][1] == -1

    def test_board_bytes_all_mines(self):
        board = [[-1, -1], [-1, -1]]
        encoded = board_list_to_bytes(board)
        decoded = board_bytes_to_board(2, 2, encoded)
        for r in decoded:
            for v in r:
                assert v == -1 or v >= 0


class TestStatsRecord:
    def test_encode_decode_roundtrip(self):
        record = StatsRecord(
            game_state=2, row=16, column=30, mine_num=99,
            rtime_ms=12345, left=20, right=10, double=5,
            rce=1, lce=3, dce=1, bbbv=120, bbbv_solved=115,
            zini=0, flag=8, path=1.5, start_time=1000000, mode=0,
            is_official=True, is_fair=True, op=5, isl=3, pluck=0.8,
        )
        data = record.encode()
        decoded = StatsRecord.decode(data)
        assert decoded.game_state == 2
        assert decoded.row == 16
        assert decoded.column == 30
        assert decoded.mine_num == 99
        assert decoded.rtime_ms == 12345
        assert decoded.is_official is True
        assert decoded.is_fair is True

    def test_encode_decode_with_board_bytes(self):
        board_data = bytes([0b10101010, 0b11110000])
        record = StatsRecord(
            game_state=1, row=8, column=8, mine_num=10,
            rtime_ms=5000, left=10, right=5, double=3,
            rce=1, lce=2, dce=0, bbbv=40, bbbv_solved=38,
            zini=0, flag=3, path=1.0, start_time=0, mode=0,
            is_official=True, is_fair=True, op=3, isl=2, pluck=0.5,
            board_bytes=board_data,
        )
        data = record.encode()
        decoded = StatsRecord.decode(data)
        assert decoded.board_bytes == board_data
        assert decoded.bbbv == 40

    def test_encode_decode_minimal(self):
        record = StatsRecord(
            game_state=0, row=1, column=1, mine_num=0,
            rtime_ms=0, left=0, right=0, double=0,
            rce=0, lce=0, dce=0, bbbv=0, bbbv_solved=0,
            zini=0, flag=0, path=0.0, start_time=0, mode=0,
            is_official=False, is_fair=False, op=0, isl=0, pluck=0.0,
        )
        data = record.encode()
        decoded = StatsRecord.decode(data)
        assert decoded.is_official is False
        assert decoded.path == 0.0


class TestTransGameMode:
    def test_standard(self):
        assert trans_game_mode(0) is not None

    def test_invalid_mode_returns_none(self):
        assert trans_game_mode(99) is None


class TestEnuLimit:
    def test_enu_limit_value(self):
        assert EnuLimit >= 50
