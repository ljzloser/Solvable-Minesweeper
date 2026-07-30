from __future__ import annotations

import math
import sys
from typing import Any, Iterable, Iterator, List, Optional, Tuple

from config.constants import CELL_UNOPENED

from .core import (
    Board,
    ReplayAnalysisResult,
    ReplayEventAnnotation,
    ReplayEventContext,
    board_size,
    cell_at,
    is_mouse_event,
    neighbours,
    register_replay_analysis_rule,
)


_PLUCK_DELTA_EPSILON = 1e-12
_MAX_PLUCK_SENTINEL = sys.float_info.max / 2
_MISSING = object()


@register_replay_analysis_rule
def guess_event_rule(context: ReplayEventContext) -> ReplayAnalysisResult:
    if context.mouse is None:
        return None

    pluck_delta = _pluck_delta_from_previous_mouse_event(context)
    if pluck_delta is None or pluck_delta <= _PLUCK_DELTA_EPSILON:
        return None

    prior_game_board = context.prior_game_board()
    possibility_board = context.prior_possibility_board()
    log10_probability = _log10_probability(pluck_delta)
    global_min_probability = _global_min_probability(prior_game_board, possibility_board)
    non_frontier_probability = _non_frontier_probability(prior_game_board, possibility_board)

    return ReplayEventAnnotation(
        severity="warning",
        key="guess",
        text=(
            f"猜雷（{_format_cell_prefix(context)}安全概率 log10 "
            f"{_format_probability_log10(log10_probability)}，"
            f"全局最小雷概率 {_format_probability(global_min_probability)}，"
            f"非前沿区雷概率 {_format_probability(non_frontier_probability)}）"
        ),
        params=(
            log10_probability,
            pluck_delta,
            global_min_probability,
            non_frontier_probability,
            context.mouse.row,
            context.mouse.column,
        ),
    )


def _pluck_delta_from_previous_mouse_event(
    context: ReplayEventContext,
) -> Optional[float]:
    current_pluck = _context_pluck(context)
    previous_pluck = _previous_mouse_pluck(context)
    if current_pluck is None or previous_pluck is None:
        return None
    if _is_max_pluck(previous_pluck):
        return None
    if _is_max_pluck(current_pluck):
        return math.inf
    if not math.isfinite(current_pluck) or not math.isfinite(previous_pluck):
        return None
    return current_pluck - previous_pluck


def _previous_mouse_pluck(context: ReplayEventContext) -> Optional[float]:
    for index in range(context.index - 1, -1, -1):
        record = context.records[index]
        if is_mouse_event(getattr(record, "event", None)):
            pluck = _record_pluck(record)
            if pluck is None:
                pluck = _video_pluck_at_event_index(context.video, index)
            if pluck is not None:
                return pluck
    return None


def _context_pluck(context: ReplayEventContext) -> Optional[float]:
    pluck = _record_pluck(context.record)
    if pluck is not None:
        return pluck
    return _video_pluck_at_event_index(context.video, context.index)


def _record_pluck(record: Any) -> Optional[float]:
    key_dynamic_params = getattr(record, "key_dynamic_params", None)
    try:
        pluck = getattr(key_dynamic_params, "pluck")
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    try:
        return float(pluck)
    except (TypeError, ValueError):
        return None


def _video_pluck_at_event_index(video: Any, event_index: int) -> Optional[float]:
    original_event_index = _video_current_event_index(video)
    try:
        setattr(video, "current_event_id", event_index)
        return _to_float(getattr(video, "pluck"))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    finally:
        _restore_video_current_event_index(video, original_event_index)


def _video_current_event_index(video: Any) -> Any:
    try:
        return getattr(video, "current_event_id")
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return _MISSING


def _restore_video_current_event_index(video: Any, event_index: Any) -> None:
    if event_index is _MISSING:
        return
    try:
        setattr(video, "current_event_id", event_index)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_max_pluck(value: float) -> bool:
    return value >= _MAX_PLUCK_SENTINEL


def _log10_probability(pluck_delta: float) -> float:
    if math.isinf(pluck_delta):
        return -math.inf
    return -pluck_delta


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
    cells = _non_frontier_cells(game_board)
    if not cells:
        return math.nan
    probabilities = [
        _cell_probability(possibility_board, row, column)
        for row, column in cells
    ]
    return _mean_probability(probabilities)


def _cell_probability(board: Board, row: int, column: int) -> float:
    try:
        return float(board[row][column])
    except (IndexError, TypeError, ValueError):
        return math.nan


def _unknown_cells(game_board: Optional[Board]) -> Iterator[Tuple[int, int]]:
    if game_board is None:
        return
    row_count, column_count = board_size(game_board)
    for row in range(row_count):
        for column in range(column_count):
            if cell_at(game_board, row, column) == CELL_UNOPENED:
                yield row, column


def _non_frontier_cells(game_board: Optional[Board]) -> List[Tuple[int, int]]:
    if game_board is None:
        return []
    row_count, column_count = board_size(game_board)
    return [
        (row, column)
        for row, column in _unknown_cells(game_board)
        if not _touches_number_cell(game_board, row, column, row_count, column_count)
    ]


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
    valid_probabilities = [p for p in probabilities if _is_valid_probability(p)]
    if not valid_probabilities:
        return math.nan
    return min(valid_probabilities)


def _mean_probability(probabilities: Iterable[float]) -> float:
    valid_probabilities = [p for p in probabilities if _is_valid_probability(p)]
    if not valid_probabilities:
        return math.nan
    return sum(valid_probabilities) / len(valid_probabilities)


def _is_valid_probability(value: float) -> bool:
    return math.isfinite(value) and value >= 0


def _format_cell_prefix(context: ReplayEventContext) -> str:
    if context.mouse is None or context.mouse.row is None or context.mouse.column is None:
        return ""
    return f"{context.mouse.row + 1},{context.mouse.column + 1}，"


def _format_probability(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.3f}"


def _format_probability_log10(value: float) -> str:
    if math.isinf(value):
        return "-inf" if value < 0 else "inf"
    if math.isnan(value):
        return "nan"
    return f"{value:.3f}"
