from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .core import (
    ReplayAnalysisResult,
    ReplayEventAnnotation,
    ReplayEventContext,
    is_mouse_event,
    register_replay_analysis_rule,
    unwrap_mouse_event,
)


Cell = Tuple[int, int]


@dataclass
class FlagContribution:
    row: int
    column: int
    dce: float = 0.0
    bbbv_solved: float = 0.0
    dce_cells: Tuple[Cell, ...] = ()


_FLAG_EVENT_CACHE: Dict[int, Tuple[int, int, Dict[int, ReplayEventAnnotation]]] = {}


@register_replay_analysis_rule
def flag_event_rule(context: ReplayEventContext) -> ReplayAnalysisResult:
    annotations = _flag_event_annotations(context)
    return annotations.get(context.index)


def _flag_event_annotations(context: ReplayEventContext) -> Dict[int, ReplayEventAnnotation]:
    records_key = id(context.records)
    cached = _FLAG_EVENT_CACHE.get(id(context.video))
    if cached is not None and cached[0] == records_key and cached[1] == len(context.records):
        return cached[2]

    annotations = _build_flag_event_annotations(context)
    _FLAG_EVENT_CACHE[id(context.video)] = (records_key, len(context.records), annotations)
    return annotations


def _build_flag_event_annotations(
    context: ReplayEventContext,
) -> Dict[int, ReplayEventAnnotation]:
    flags_by_index: Dict[int, FlagContribution] = {}
    active_flags: List[Tuple[int, Cell]] = []

    previous_mouse_record = None
    for index, record in enumerate(context.records):
        mouse_event = _mouse_event_record(context, index)
        if mouse_event is None:
            continue

        _mouse_name, row, column = mouse_event
        if row is None or column is None:
            previous_mouse_record = record
            continue

        if _counter_delta(previous_mouse_record, record, "flag") > 0:
            flag = FlagContribution(row=row, column=column)
            flags_by_index[index] = flag
            active_flags.append((index, (row, column)))
        elif _counter_delta(previous_mouse_record, record, "flag") < 0:
            _remove_active_flag(active_flags, row, column)

        dce_delta = _counter_delta(previous_mouse_record, record, "dce", "double_ce")
        if dce_delta > 0:
            bbbv_delta = _counter_delta(previous_mouse_record, record, "bbbv_solved")
            nearby_flags = [
                flag_index
                for flag_index, flag_cell in active_flags
                if _is_nearby(flag_cell, (row, column))
            ]
            if nearby_flags:
                dce_share = dce_delta / len(nearby_flags)
                bbbv_share = bbbv_delta / len(nearby_flags)
                for flag_index in nearby_flags:
                    flag = flags_by_index[flag_index]
                    flag.dce += dce_share
                    flag.bbbv_solved += bbbv_share
                    flag.dce_cells = _append_unique_cell(flag.dce_cells, (row, column))

        previous_mouse_record = record

    return {
        event_index: _annotation_for_flag(event_index, flag)
        for event_index, flag in flags_by_index.items()
    }


def _annotation_for_flag(
    event_index: int,
    flag: FlagContribution,
) -> ReplayEventAnnotation:
    dce_text = _format_number(flag.dce)
    bbbv_text = _format_number(flag.bbbv_solved)
    return ReplayEventAnnotation(
        severity=_flag_event_severity(flag.dce, flag.bbbv_solved),
        key="标雷",
        text=f"dce{dce_text}，bbbv_solved{bbbv_text}",
        params=(flag.dce, flag.bbbv_solved),
        event_index=event_index,
        highlight_cells=((flag.row, flag.column), *flag.dce_cells),
    )


def _mouse_event_record(
    context: ReplayEventContext,
    index: int,
) -> Optional[Tuple[str, Optional[int], Optional[int]]]:
    record = context.records[index]
    event = getattr(record, "event", None)
    if not is_mouse_event(event):
        return None
    mouse = unwrap_mouse_event(event, context.pix_size)
    if mouse is None or mouse.mouse in {"mv", "mc", "mr"}:
        return None
    return mouse.mouse, mouse.row, mouse.column


def _counter_delta(
    previous_record: Optional[Any],
    current_record: Any,
    *counter_names: str,
) -> int:
    for counter_name in counter_names:
        previous_value = _record_counter(previous_record, counter_name)
        current_value = _record_counter(current_record, counter_name)
        if previous_value is None:
            previous_value = 0
        if current_value is not None:
            return current_value - previous_value
    return 0


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


def _remove_active_flag(active_flags: List[Tuple[int, Cell]], row: int, column: int) -> None:
    for index in range(len(active_flags) - 1, -1, -1):
        if active_flags[index][1] == (row, column):
            del active_flags[index]
            return


def _is_nearby(left: Cell, right: Cell) -> bool:
    return abs(left[0] - right[0]) <= 1 and abs(left[1] - right[1]) <= 1


def _append_unique_cell(cells: Tuple[Cell, ...], cell: Cell) -> Tuple[Cell, ...]:
    if cell in cells:
        return cells
    return (*cells, cell)


def _flag_event_severity(dce: float, bbbv_solved: float) -> str:
    if bbbv_solved == 0:
        return "error"
    if bbbv_solved > dce + 1:
        return "success"
    if bbbv_solved < dce + 1:
        return "warning"
    return "info"


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"
