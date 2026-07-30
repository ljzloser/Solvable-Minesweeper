from __future__ import annotations

import math
from typing import Any, Iterable, Iterator, Optional, Tuple

from PyQt5.QtCore import QCoreApplication

from config.constants import CELL_UNOPENED

from .core import (
    Board,
    ReplayEvent,
    ReplayEventContext,
    ReplayEventManager,
    board_size,
    cell_at,
    extract_game_board,
    extract_possibility_board,
    register_replay_event_manager,
    neighbours,
)
from .format import format_pluck, format_probability_percent


_PLUCK_DELTA_EPSILON = 1e-12
_MISSING = object()
_translate = QCoreApplication.translate


class GuessEvent(ReplayEvent):
    def __init__(
        self,
        event_index: int,
        time: float,
        pluck_delta: float,
        global_min_probability: float,
        non_frontier_probability: float,
        row: int,
        column: int,
        current_pluck: float,
    ):
        self.pluck_delta = pluck_delta
        self.global_min_probability = global_min_probability
        self.non_frontier_probability = non_frontier_probability
        self.current_pluck = current_pluck
        super().__init__(
            event_index=event_index,
            time=time,
            coordinate=(row, column),
        )

    def type_text(self) -> str:
        return _translate("ReplayAnalysis", "猜雷")

    def detail_text(self) -> str:
        text = _translate(
            "ReplayAnalysis",
            "pluck={pluck}(+{pluck_diff})，雷{mine}，最小{minimum}，密度{density}",
        )
        return (
            text
            .replace("{pluck}", format_pluck(self.current_pluck))
            .replace("{pluck_diff}", format_pluck(self.pluck_delta))
            .replace("{mine}", format_probability_percent(self.mine_probability()))
            .replace("{minimum}", format_probability_percent(self.global_min_probability))
            .replace("{density}", format_probability_percent(self.non_frontier_probability))
        )

    def severity(self) -> str:
        mine_probability = 1 - 10 ** (-self.pluck_delta)
        if math.isclose(mine_probability, self.global_min_probability):
            return "success"
        if mine_probability > self.non_frontier_probability:
            return "warning"
        if math.isclose(self.global_min_probability, 0.0):
            return "warning"
        return "info"

    def highlight_cells(self) -> Tuple[Tuple[int, int], ...]:
        return (self.coordinate,) if self.coordinate is not None else ()


@register_replay_event_manager
class GuessEventManager(ReplayEventManager):
    def reset(self, video: Any) -> None:
        video.analyse_for_features(["pluck"])
        self.previous_mouse_pluck: Optional[float] = None
        self.prior_game_board: Optional[Board] = None
        self.prior_possibility_board: Optional[Board] = None

    def handle(self, context: ReplayEventContext) -> Iterable[ReplayEvent]:
        if context.mouse is None or context.mouse.is_mouse("mv", "mc", "mr"):
            return ()

        current_pluck = _context_pluck(context)
        previous_pluck = self.previous_mouse_pluck
        self.previous_mouse_pluck = current_pluck
        if previous_pluck is None:
            return ()
        pluck_delta = current_pluck - previous_pluck
        if pluck_delta <= _PLUCK_DELTA_EPSILON:
            return ()

        self.prior_game_board = self._extract_prior_game_board(context)
        self.prior_possibility_board = self._extract_prior_possibility_board(context)
        global_min_probability = _global_min_probability(
            self.prior_game_board,
            self.prior_possibility_board,
        )
        non_frontier_probability = _non_frontier_probability(
            self.prior_game_board,
            self.prior_possibility_board,
        )
        return (
            GuessEvent(
                event_index=context.index,
                time=context.time,
                pluck_delta=pluck_delta,
                global_min_probability=global_min_probability,
                non_frontier_probability=non_frontier_probability,
                row=context.mouse.row,
                column=context.mouse.column,
                current_pluck=current_pluck,
            ),
        )

    def _extract_prior_game_board(self, context: ReplayEventContext) -> Optional[Board]:
        return extract_game_board(getattr(context.record, "prior_game_board", None))

    def _extract_prior_possibility_board(self, context: ReplayEventContext) -> Optional[Board]:
        return extract_possibility_board(getattr(context.record, "prior_game_board", None))


def _context_pluck(context: ReplayEventContext) -> float:
    pluck = _record_pluck(context.record)
    if pluck is not None:
        return pluck
    return _video_pluck_at_event_index(context.video, context.index)


def _record_pluck(record: Any) -> Optional[float]:
    key_dynamic_params = getattr(record, "key_dynamic_params", None)
    try:
        return float(getattr(key_dynamic_params, "pluck"))
    except (AttributeError, RuntimeError):
        return None


def _video_pluck_at_event_index(video: Any, event_index: int) -> float:
    original_event_index = _video_current_event_index(video)
    try:
        setattr(video, "current_event_id", event_index)
        return float(getattr(video, "pluck"))
    finally:
        _restore_video_current_event_index(video, original_event_index)


def _video_current_event_index(video: Any) -> Any:
    try:
        return getattr(video, "current_event_id")
    except (AttributeError, RuntimeError):
        return _MISSING


def _restore_video_current_event_index(video: Any, event_index: Any) -> None:
    if event_index is _MISSING:
        return
    try:
        setattr(video, "current_event_id", event_index)
    except (AttributeError, RuntimeError):
        return


def _global_min_probability(
    game_board: Optional[Board],
    possibility_board: Optional[Board],
) -> float:
    if game_board is None or possibility_board is None:
        return math.nan
    probabilities = [
        _cell_probability(possibility_board, row, column)
        for row, column in _unknown_cells(game_board)
    ]
    return _min_probability(probabilities)


def _non_frontier_probability(
    game_board: Optional[Board],
    possibility_board: Optional[Board],
) -> float:
    if game_board is None or possibility_board is None:
        return math.nan
    row_count, column_count = board_size(game_board)
    for row, column in _unknown_cells(game_board):
        if not _touches_number_cell(game_board, row, column, row_count, column_count):
            return _cell_probability(possibility_board, row, column)
    return math.nan


def _cell_probability(board: Board, row: int, column: int) -> float:
    return float(board[row][column])


def _unknown_cells(game_board: Optional[Board]) -> Iterator[Tuple[int, int]]:
    if game_board is None:
        return
    row_count, column_count = board_size(game_board)
    for row in range(row_count):
        for column in range(column_count):
            if cell_at(game_board, row, column) == CELL_UNOPENED:
                yield row, column


def _touches_number_cell(
    game_board: Board,
    row: int,
    column: int,
    row_count: int,
    column_count: int,
) -> bool:
    return any(
        _is_number_cell(cell_at(game_board, next_row, next_column))
        for next_row, next_column in neighbours(row, column, row_count, column_count)
    )


def _is_number_cell(value: Any) -> bool:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return False
    return 1 <= value <= 8


def _min_probability(probabilities: Iterable[float]) -> float:
    probabilities = list(probabilities)
    if not probabilities:
        return math.nan
    return min(probabilities)
