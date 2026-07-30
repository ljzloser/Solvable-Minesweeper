from __future__ import annotations

from typing import Any, List, Optional, Tuple

from PyQt5.QtCore import QCoreApplication

from .core import (
    ReplayEvent,
    ReplayEventContext,
    ReplayEventManager,
    is_mouse_event,
    register_replay_event_manager,
    unwrap_mouse_event,
)
from .format import format_interval_ms


ComboClick = Tuple[int, Any, float, int, int]
_translate = QCoreApplication.translate


class ComboClickEvent(ReplayEvent):
    def __init__(self, clicks: List[ComboClick]):
        self.clicks = tuple(clicks)
        intervals = [
            clicks[index][2] - clicks[index - 1][2]
            for index in range(1, len(clicks))
        ]
        self.length = len(clicks)
        self.max_interval = max(intervals)
        self.min_interval = min(intervals)
        self.average_interval = sum(intervals) / len(intervals)
        super().__init__(
            event_index=clicks[-1][0],
            time=clicks[-1][2],
            coordinate=(clicks[-1][3], clicks[-1][4]),
            params=(self.length, self.max_interval, self.min_interval, self.average_interval),
        )

    def type_text(self) -> str:
        return _translate("ReplayAnalysis", "连击")

    def detail_text(self) -> str:
        text = _translate(
            "ReplayAnalysis",
            "长度{length}，间隔最大{max_interval}，最小{min_interval}，平均{average_interval}",
        )
        return (
            text
            .replace("{length}", str(self.length))
            .replace("{max_interval}", format_interval_ms(self.max_interval))
            .replace("{min_interval}", format_interval_ms(self.min_interval))
            .replace("{average_interval}", format_interval_ms(self.average_interval))
        )

    def highlight_cells(self) -> Tuple[Tuple[int, int], ...]:
        return tuple((row, column) for _, _, _, row, column in self.clicks)


@register_replay_event_manager
class ComboClickEventManager(ReplayEventManager):
    def reset(self, _video: Any) -> None:
        self.sequence: List[ComboClick] = []
        self.previous_action: Optional[Tuple[int, Any, str, float, int, int]] = None

    def handle(self, context: ReplayEventContext) -> Tuple[ReplayEvent, ...]:
        action = _mouse_action_record(context, context.index)
        if action is None:
            return ()

        click = _lce_click_from_record(*action, self.previous_action[1] if self.previous_action else None)
        emitted = self._handle_click(click)
        if click is None and self.previous_action is not None and _counter_increased(
            self.previous_action[1],
            action[1],
            "rce",
            "right_ce",
            "dce",
            "double_ce",
        ):
            emitted = self._flush_sequence()
        self.previous_action = action
        return emitted

    def finish(self) -> Tuple[ReplayEvent, ...]:
        return self._flush_sequence()

    def _handle_click(self, click: Optional[ComboClick]) -> Tuple[ReplayEvent, ...]:
        if click is None:
            return ()
        if not self.sequence:
            self.sequence = [click]
            return ()
        if _is_adjacent_cell(self.sequence[-1], click):
            self.sequence.append(click)
            return ()
        emitted = self._flush_sequence()
        self.sequence = [click]
        return emitted

    def _flush_sequence(self) -> Tuple[ReplayEvent, ...]:
        if len(self.sequence) < 3:
            self.sequence = []
            return ()
        event = ComboClickEvent(self.sequence)
        self.sequence = []
        return (event,)


def _lce_click_from_record(
    index: int,
    record: Any,
    mouse_name: str,
    event_time: float,
    row: int,
    column: int,
    previous_record: Optional[Any] = None,
) -> Optional[ComboClick]:
    if mouse_name not in {"lr", "l"}:
        return None
    if not _counter_increased(previous_record, record, "lce", "left_ce"):
        return None
    return index, record, event_time, row, column


def _mouse_action_record(
    context: ReplayEventContext,
    index: int,
) -> Optional[Tuple[int, Any, str, float, int, int]]:
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
        if current_value is not None and current_value - previous_value == 1:
            return True
    return False


def _record_counter(record: Optional[Any], counter_name: str) -> Optional[int]:
    if record is None:
        return None
    key_dynamic_params = getattr(record, "key_dynamic_params", None)
    for source in (key_dynamic_params, record):
        try:
            return int(getattr(source, counter_name))
        except (AttributeError, RuntimeError):
            continue
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
