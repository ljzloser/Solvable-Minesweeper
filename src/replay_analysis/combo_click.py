from __future__ import annotations

from typing import Any, List, Optional, Tuple

from PyQt5.QtCore import QCoreApplication

from .core import (
    ReplayAnalysisResult,
    ReplayEventAnnotation,
    ReplayEventContext,
    is_mouse_event,
    register_replay_analysis_rule,
    unwrap_mouse_event,
)


ComboClick = Tuple[int, Any, float, int, int]
_translate = QCoreApplication.translate


@register_replay_analysis_rule
def combo_click_event_rule(context: ReplayEventContext) -> ReplayAnalysisResult:
    current_click = _lce_click_at(context, context.index)
    if current_click is None:
        return None
    if _next_lce_click_continues(context, current_click):
        return None

    clicks = _collect_combo_clicks(context, current_click)
    if len(clicks) < 3:
        return None

    intervals = [
        clicks[index][2] - clicks[index - 1][2]
        for index in range(1, len(clicks))
    ]
    min_interval = min(intervals)
    max_interval = max(intervals)
    average_interval = sum(intervals) / len(intervals)

    text = _translate(
        "ReplayAnalysis",
        "长度{length}，间隔最大{max_interval}，最小{min_interval}，平均{average_interval}",
    )
    text = (
        text
        .replace("{length}", str(len(clicks)))
        .replace("{max_interval}", _format_interval_ms(max_interval))
        .replace("{min_interval}", _format_interval_ms(min_interval))
        .replace("{average_interval}", _format_interval_ms(average_interval))
    )

    return ReplayEventAnnotation(
        severity="info",
        key=_translate("ReplayAnalysis", "连击"),
        text=text,
        params=(len(clicks), max_interval, min_interval, average_interval),
        highlight_cells=tuple((row, column) for _, _, _, row, column in clicks),
    )


def _collect_combo_clicks(
    context: ReplayEventContext,
    current_click: ComboClick,
) -> List[ComboClick]:
    clicks = [current_click]
    next_click = current_click
    for previous_click in _iter_previous_lce_clicks(context, current_click[0]):
        if not _is_adjacent_cell(previous_click, next_click):
            break
        clicks.append(previous_click)
        next_click = previous_click
    clicks.reverse()
    return clicks


def _next_lce_click_continues(
    context: ReplayEventContext,
    current_click: ComboClick,
) -> bool:
    next_click = _next_lce_click(context, current_click[0])
    if next_click is None:
        return False
    return _is_adjacent_cell(current_click, next_click)


def _iter_previous_lce_clicks(
    context: ReplayEventContext,
    before_index: int,
) -> List[ComboClick]:
    clicks = []
    next_index = before_index
    while True:
        click = _previous_lce_click(context, next_index)
        if click is None:
            return clicks
        clicks.append(click)
        next_index = click[0]
    return clicks


def _previous_lce_click(
    context: ReplayEventContext,
    before_index: int,
) -> Optional[ComboClick]:
    for index in range(before_index - 1, -1, -1):
        action = _mouse_action_record(context, index)
        if action is None:
            continue
        click = _lce_click_from_record(context, *action)
        if click is not None:
            return click
        if _breaks_lce_chain(context, *action):
            return None
    return None


def _next_lce_click(
    context: ReplayEventContext,
    after_index: int,
) -> Optional[ComboClick]:
    for index in range(after_index + 1, len(context.records)):
        action = _mouse_action_record(context, index)
        if action is None:
            continue
        click = _lce_click_from_record(context, *action)
        if click is not None:
            return click
        if _breaks_lce_chain(context, *action):
            return None
    return None


def _lce_click_at(context: ReplayEventContext, index: int) -> Optional[ComboClick]:
    if context.mouse is None:
        return None
    return _lce_click_from_record(
        context,
        index,
        context.record,
        context.mouse.mouse,
        context.time,
        context.mouse.row,
        context.mouse.column,
        context.previous_record,
    )


def _lce_click_from_record(
    context: ReplayEventContext,
    index: int,
    record: Any,
    mouse_name: str,
    event_time: float,
    row: Optional[int],
    column: Optional[int],
    previous_record: Optional[Any] = None,
) -> Optional[ComboClick]:
    if mouse_name not in {"lr", "l"}:
        return None
    if row is None or column is None:
        return None
    if previous_record is None:
        previous_record = _previous_mouse_action_record(context, index)
        previous_record = previous_record[1] if previous_record is not None else None
    if not _counter_increased(previous_record, record, "lce", "left_ce"):
        return None
    return index, record, event_time, row, column


def _breaks_lce_chain(
    context: ReplayEventContext,
    index: int,
    record: Any,
    _mouse_name: str,
    _event_time: float,
    _row: Optional[int],
    _column: Optional[int],
) -> bool:
    previous_record = _previous_mouse_action_record(context, index)
    previous_record = previous_record[1] if previous_record is not None else None
    return _counter_increased(previous_record, record, "rce", "right_ce", "dce", "double_ce")


def _previous_mouse_action_record(
    context: ReplayEventContext,
    before_index: int,
) -> Optional[Tuple[int, Any, str, float, Optional[int], Optional[int]]]:
    for index in range(before_index - 1, -1, -1):
        action = _mouse_action_record(context, index)
        if action is not None:
            return action
    return None


def _mouse_action_record(
    context: ReplayEventContext,
    index: int,
) -> Optional[Tuple[int, Any, str, float, Optional[int], Optional[int]]]:
    record = context.records[index]
    event = getattr(record, "event", None)
    if not is_mouse_event(event):
        return None
    mouse = unwrap_mouse_event(event, context.pix_size)
    if mouse is None or mouse.mouse in {"mv", "mc", "mr"}:
        return None
    return index, record, mouse.mouse, _record_time(record), mouse.row, mouse.column


def _counter_increased(
    previous_record: Optional[Any],
    current_record: Any,
    *counter_names: str,
) -> bool:
    for counter_name in counter_names:
        previous_value = _record_counter(previous_record, counter_name)
        current_value = _record_counter(current_record, counter_name)
        if previous_value is None:
            previous_value = 0
        if previous_value is not None and current_value is not None and current_value == previous_value + 1:
            return True
    return False


def _record_counter(record: Optional[Any], counter_name: str) -> Optional[int]:
    if record is None:
        return None
    key_dynamic_params = getattr(record, "key_dynamic_params", None)
    for source in (key_dynamic_params, record):
        try:
            value = getattr(source, counter_name)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def _is_adjacent_cell(left: ComboClick, right: ComboClick) -> bool:
    row_delta = abs(left[3] - right[3])
    column_delta = abs(left[4] - right[4])
    return row_delta + column_delta == 1


def _record_time(record: Any) -> float:
    try:
        return float(getattr(record, "time", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _format_interval_ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f}ms"
