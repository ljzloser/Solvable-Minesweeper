from __future__ import annotations

from typing import Any, Optional, Tuple

from .core import (
    ReplayAnalysisResult,
    ReplayEventAnnotation,
    ReplayEventContext,
    is_mouse_event,
    register_replay_analysis_rule,
    unwrap_mouse_event,
)


@register_replay_analysis_rule
def one_point_five_click_event_rule(context: ReplayEventContext) -> ReplayAnalysisResult:
    if context.mouse is None or not context.mouse.is_mouse("lr", "rr", "l", "r"):
        return None

    left_press = _previous_mouse_action_record(context, before_index=context.index)
    if left_press is None or left_press[2] not in {"lc", "cc"}:
        return None
    if not _counter_increased(left_press[1], context.record, "dce", "double_ce"):
        return None

    right_press = _previous_mouse_action_record(context, before_index=left_press[0])
    if right_press is None or right_press[2] != "rc":
        return None

    previous_mouse_before_right = _previous_mouse_action_record(context, before_index=right_press[0])
    previous_record_before_right = (
        previous_mouse_before_right[1] if previous_mouse_before_right is not None else None
    )
    if not _counter_increased(previous_record_before_right, right_press[1], "rce", "right_ce"):
        return None

    right_left_interval = left_press[3] - right_press[3]
    flag_double_interval = context.time - right_press[3]

    return ReplayEventAnnotation(
        severity="info",
        key="1.5click",
        text=(
            f"右左间隔{_format_interval_ms(right_left_interval)}，"
            f"标双间隔{_format_interval_ms(flag_double_interval)}"
        ),
        params=(right_left_interval, flag_double_interval),
        highlight_cells=_unique_cells(
            (right_press[4], right_press[5]),
            (context.mouse.row, context.mouse.column),
        ),
    )


def _previous_mouse_action_record(
    context: ReplayEventContext,
    before_index: int,
) -> Optional[Tuple[int, Any, str, float, Optional[int], Optional[int]]]:
    for index in range(before_index - 1, -1, -1):
        record = context.records[index]
        event = getattr(record, "event", None)
        if not is_mouse_event(event):
            continue
        mouse = unwrap_mouse_event(event, context.pix_size)
        if mouse is None:
            continue
        if mouse.mouse in {"mv", "mc", "mr"}:
            continue
        return index, record, mouse.mouse, _record_time(record), mouse.row, mouse.column
    return None


def _unique_cells(*cells: Tuple[Optional[int], Optional[int]]) -> Tuple[Tuple[int, int], ...]:
    result = []
    seen = set()
    for row, column in cells:
        if row is None or column is None:
            continue
        cell = (row, column)
        if cell in seen:
            continue
        result.append(cell)
        seen.add(cell)
    return tuple(result)


def _counter_increased(
    previous_record: Optional[Any],
    current_record: Any,
    *counter_names: str,
) -> bool:
    for counter_name in counter_names:
        previous_value = _record_counter(previous_record, counter_name)
        current_value = _record_counter(current_record, counter_name)
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


def _record_time(record: Any) -> float:
    try:
        return float(getattr(record, "time", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _format_interval_ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f}ms"
